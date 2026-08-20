"""MCP server for Civ7 debug console - allows AI agents to execute JavaScript commands."""

import argparse
import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP, Context, Image
except ModuleNotFoundError as error:  # MCP 2 renamed FastMCP to MCPServer
    if error.name != "mcp.server.fastmcp":
        raise
    from mcp.server.mcpserver import MCPServer as FastMCP, Context, Image
from mcp.server.session import ServerSession

from .connection import ConnectionConfig, ConnectionManager, ConnectionState
from .screenshot import ScreenshotError, capture_game_window
from . import cdp, game_tools


@dataclass
class Civ7Context:
    """Lifespan context holding the connection to Civ7."""
    connection: ConnectionManager


@asynccontextmanager
async def civ7_lifespan(server: FastMCP) -> AsyncIterator[Civ7Context]:
    """Manage Civ7 connection lifecycle."""
    global _connection
    config = ConnectionConfig(host=_host, port=_port)
    connection = ConnectionManager(config, on_protocol_change=_on_protocol_change)
    await connection.start()
    _connection = connection
    try:
        yield Civ7Context(connection=connection)
    finally:
        _connection = None
        await connection.stop()


# Module-level config set by main() before server starts
_host = "127.0.0.1"
_port = 4318
# Set by civ7_lifespan; lets parameterless handlers (resources) reach the
# connection, since resource functions with extra params become URI templates
_connection: Optional[ConnectionManager] = None

# Pending transport-switch notice, surfaced once in the next execute_js
# result (internal JSON-returning tools skip it so parsing stays clean).
_protocol_notice: Optional[str] = None


def _on_protocol_change(new: Optional[str], old: Optional[str]) -> None:
    global _protocol_notice
    if new == "cdp":
        _protocol_notice = (
            f"[transport] tuner port unreachable — switched to CDP fallback "
            f"(port {cdp.CDP_PORT}, same JS context; the game suspends the tuner "
            f"during MP/hotseat sessions)"
        )
    elif new == "tuner" and old == "cdp":
        _protocol_notice = "[transport] tuner port is back — switched from CDP fallback to tuner"
    print(f"civ7-mcp: active protocol {old} -> {new}", file=sys.stderr)


mcp = FastMCP("Civ7 Debug Console", lifespan=civ7_lifespan)


@mcp.tool()
async def execute_js(
    code: str,
    ctx: Context[ServerSession, Civ7Context],
) -> str:
    """Execute JavaScript code on the Civ7 debug console and return the result.

    Use this to interact with Civilization 7's game engine through its debug port.
    Send any valid JavaScript expression or multi-line script. The last expression's
    value is returned as the response.

    Examples:
        - "1+1" returns "2"
        - "GameplayMap.getGridWidth()" returns the map width
        - "Players.getAliveMajorIds()" returns alive player IDs
    """
    response = await _run_js(ctx, code)
    global _protocol_notice
    if _protocol_notice and not response.startswith("ERROR:"):
        response = f"{_protocol_notice}\n{response}"
        _protocol_notice = None
    return response


async def _run_js(ctx: Context[ServerSession, Civ7Context], code: str) -> str:
    """Internal: run JS through the shared connection (tuner, or the CDP
    fallback while the tuner is suspended) with uniform error text."""
    connection = ctx.request_context.lifespan_context.connection

    # send_command falls back to CDP by itself when the tuner is down — only
    # a None (both transports failed / timed out) warrants a diagnosis.
    response = await connection.send_command(code)

    if response is None:
        if connection.state == ConnectionState.CONNECTED:
            return "ERROR: Command timed out or connection lost."
        diagnosis = await asyncio.to_thread(game_tools.diagnose_disconnect, _port)
        return f"ERROR: Not connected to Civ7 debug port. Diagnosis: {diagnosis}"

    return response


@mcp.tool()
async def screenshot(save_path: str = "", max_width: int = 1568) -> Image:
    """Capture a screenshot of the running Civ 7 game window and return it as an image.

    This is an OS-level capture of the game window (the debug port itself is
    text-only). The window is brought to the foreground first. Falls back to
    the primary monitor if the Civ 7 window can't be found. Combine with
    execute_js camera calls (e.g. Camera.lookAtPlot(x, y)) to frame the shot.

    Args:
        save_path: Optional file path to also save the PNG to disk.
        max_width: Downscale to this width in pixels (default 1568, good for
            AI vision). Pass 0 for full resolution.
    """
    try:
        png = await asyncio.to_thread(capture_game_window, max_width)
    except ScreenshotError as e:
        raise RuntimeError(str(e)) from e

    if save_path:
        Path(save_path).write_bytes(png)

    return Image(data=png, format="png")


@mcp.resource("civ7://status")
async def get_status() -> str:
    """Get current connection status to the Civ7 debug port."""
    state = _connection.state if _connection is not None else ConnectionState.DISCONNECTED

    if state == ConnectionState.CONNECTED:
        return f"Connected to Civ7 at {_host}:{_port} (protocol: tuner)"

    # Tuner is down — check whether the CDP fallback carries commands. A live
    # round-trip is the truth, not just an open port.
    if _connection is not None:
        pong = await _connection.send_command("'pong'")
        if pong == "pong":
            return (
                f"Tuner port {_port} closed — commands are flowing over the CDP "
                f"fallback (port {cdp.CDP_PORT}, protocol: cdp). The game suspends "
                f"the tuner during MP/hotseat; it reopens at the main menu."
            )

    diagnosis = await asyncio.to_thread(game_tools.diagnose_disconnect, _port)
    verb = "Connecting to" if state == ConnectionState.CONNECTING else "Disconnected from"
    return f"{verb} Civ7 ({_host}:{_port}). Diagnosis: {diagnosis}"


@mcp.tool()
async def get_game_state(
    ctx: Context[ServerSession, Civ7Context],
    sections: str = "overview,players,map",
) -> str:
    """Get a structured JSON snapshot of the current game state.

    Replaces hand-written execute_js boilerplate for the most common queries.
    If no game is loaded, returns {inGame: false} with the current screen stack.

    Args:
        sections: Comma-separated list of: overview (turn/age), players
            (civ, gold, research, counts), cities (name/location/pop),
            units (type/location), map (dimensions). Default: overview,players,map.
    """
    wanted = [s.strip() for s in sections.split(",") if s.strip()]
    bad = [s for s in wanted if s not in game_tools._STATE_SECTIONS]
    if bad or not wanted:
        return f"ERROR: unknown sections {bad}. Valid: {', '.join(game_tools._STATE_SECTIONS)}"
    return await _run_js(ctx, game_tools.get_game_state_js(wanted))


@mcp.tool()
async def get_screen(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Describe the current UI screen: screen stack, pressable button captions,
    any open dialog, and whether a game is loaded. Use before press_button."""
    return await _run_js(ctx, game_tools.GET_SCREEN_JS)


@mcp.tool()
async def describe_screen(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Semantic summary of what is displayed right now — for orientation.

    Returns game context (in game? turn/date), the screen composition
    (mounted UI elements collapsed to counts), the visible headings/labels a
    human would read, pressable button captions, and any open dialog text.
    Complements get_screen (raw stack, press-oriented) and screenshot
    (pixels). Works in menus and in-game.
    """
    return await _run_js(ctx, game_tools.DESCRIBE_SCREEN_JS)


@mcp.tool()
async def press_button(ctx: Context[ServerSession, Civ7Context], caption: str) -> str:
    """Press a UI button by its visible caption (case-insensitive; substring ok).

    Uses the engine-input event pattern (synthetic DOM clicks are ignored by
    the game). On a miss, returns the captions that ARE available. Use
    get_screen first to see what's pressable. Game flow reference:
    test-harness/ui-automation.md.
    """
    return await _run_js(ctx, game_tools.press_button_js(caption))


@mcp.tool()
async def reveal_map(ctx: Context[ServerSession, Civ7Context], scope: str = "human") -> str:
    """Reveal the entire map (requires a loaded game).

    Uses the same mechanism as Firaxis's own Map tuner panel
    (Visibility.revealAllPlots). Reveals terrain permanently for the chosen
    players; does not grant live visibility of units in unseen territory.

    Args:
        scope: "human" (default) reveals for human players, "all" for every
            alive major (use this in autoplay games, which have no humans),
            or a numeric player id like "0".
    """
    return await _run_js(ctx, game_tools.reveal_map_js(scope))


@mcp.tool()
async def list_civs_and_units(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Detailed review of every alive civ and all their units (requires a game).

    Per civ: localized civ/leader names, human flag, gold, city names, and the
    full unit roster (localized name, unit type, position, damage) plus
    per-type counts. For a lighter summary use get_game_state instead.
    """
    return await _run_js(ctx, game_tools.LIST_CIVS_UNITS_JS)


@mcp.tool()
async def get_continents(ctx: Context[ServerSession, Civ7Context]) -> str:
    """List every continent on the map (requires a loaded game).

    Per continent: engine id, CONTINENT_* type, localized name, tile count,
    number of cities on it, which players have cities there, and the city
    names. Useful for spatial reasoning ("which landmass is player 2 on?").
    """
    return await _run_js(ctx, game_tools.GET_CONTINENTS_JS)


@mcp.tool()
async def get_continent_size(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Size metrics for every continent (requires a loaded game).

    Per continent: tile count, share of all land and of the whole map, and
    bounding box — plus overall map land/water totals. Complements
    get_continents (which covers cities/players present).
    """
    return await _run_js(ctx, game_tools.GET_CONTINENT_SIZE_JS)


@mcp.tool()
async def get_players(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Detailed roster of every alive major player (requires a loaded game).

    Per player: localized civ/leader, human flag, team, gold, government,
    city count + capital name, unit count, and diplomacy (which other majors
    they have met / are at war with). Also lists alive independent-power ids
    (see get_citystates for their details). Lighter than list_civs_and_units,
    richer than get_game_state's players section.
    """
    return await _run_js(ctx, game_tools.GET_PLAYERS_JS)


@mcp.tool()
async def get_citystates(ctx: Context[ServerSession, Civ7Context]) -> str:
    """List all independent powers / city-states (requires a loaded game).

    Per independent: localized name, whether it is an encampment, its
    village/settlement plot, unit and city counts, its city-state type hash,
    whether a suzerain bonus has been chosen (Game.CityStates), and its
    relationship (hostile/friendly/...) toward every major player.
    """
    return await _run_js(ctx, game_tools.GET_CITYSTATES_JS)


@mcp.tool()
async def get_age(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Current age and age progression (requires a loaded game).

    Returns the AGE_* type, localized name, chronology index, turn/date, and
    Game.AgeProgressManager progress (current/max points, isAgeOver,
    countdown started). Note: do NOT try to change age progression via
    updateAgeProgressionPoints — it hard-crashes the current build (see
    test-harness/game-api-testing.md).
    """
    return await _run_js(ctx, game_tools.GET_AGE_JS)


@mcp.tool()
async def get_map_resources(
    ctx: Context[ServerSession, Civ7Context],
    include_locations: bool = False,
) -> str:
    """Scan the whole map for resources (requires a loaded game).

    Returns total resource tiles and, per resource type: RESOURCE_* type,
    localized name, resource class, and count — sorted by count.

    Args:
        include_locations: Also list every tile {x, y} per resource type
            (larger output; default False).
    """
    return await _run_js(ctx, game_tools.get_map_resources_js(include_locations))


@mcp.tool()
async def get_player_resources(
    ctx: Context[ServerSession, Civ7Context],
    player_id: int = -1,
) -> str:
    """Resources owned by a player (requires a loaded game).

    Per resource: RESOURCE_* type, localized name, class, source plot, and
    the assigned city id when the engine reports one; plus totals, counts by
    type, resources awaiting assignment, and imported count.

    Args:
        player_id: A player id, or -1 (default) for every alive major.
    """
    return await _run_js(ctx, game_tools.get_player_resources_js(player_id))


@mcp.tool()
async def get_tile(ctx: Context[ServerSession, Civ7Context], x: int, y: int) -> str:
    """Everything about one map plot (requires a loaded game).

    Terrain, biome, feature, resource, continent, owner, city and units on
    the plot, elevation, impassable/lake/fresh-water flags, natural wonder,
    river info. The 'inspect this hex' primitive.
    """
    return await _run_js(ctx, game_tools.get_tile_js(x, y))


@mcp.tool()
async def get_city(ctx: Context[ServerSession, Civ7Context], x: int, y: int) -> str:
    """Deep detail for the city at a plot (requires a loaded game).

    Name, owner, capital/town flags, populations, growth and happiness,
    net yields per type, current production + turns left, and every
    constructible (buildings/wonders) with completion state. Find city
    locations via get_game_state(sections="cities") or get_continents.
    """
    return await _run_js(ctx, game_tools.get_city_js(x, y))


@mcp.tool()
async def get_units_at(ctx: Context[ServerSession, Civ7Context], x: int, y: int) -> str:
    """Full detail for every unit on a plot (requires a loaded game).

    Type, owner, combat/commander/embarked/fortified flags, damage, moves
    remaining vs max, level, promotions, and army membership.
    """
    return await _run_js(ctx, game_tools.get_units_at_js(x, y))


@mcp.tool()
async def get_victory_progress(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Victory progress per team + legacy-path state per player (requires a game).

    Game.VictoryManager progress (victory type, current/total) mapped to the
    players on each team, plus each major's enabled/completed legacy paths
    and per-path scores. The natural assertion target for autoplay runs.
    """
    return await _run_js(ctx, game_tools.GET_VICTORY_PROGRESS_JS)


@mcp.tool()
async def get_diplomacy(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Full diplomacy matrix between majors (requires a loaded game).

    Per pair: met, at war (with war name), relationship level + localized
    name. Also a flat list of active wars.
    """
    return await _run_js(ctx, game_tools.GET_DIPLOMACY_JS)


@mcp.tool()
async def get_tech_civics(ctx: Context[ServerSession, Civ7Context], player_id: int) -> str:
    """A player's tech + civic tree state (requires a loaded game).

    For both trees: current research (node, progress, turns left) and the
    list of completed nodes.
    """
    return await _run_js(ctx, game_tools.get_tech_civics_js(player_id))


@mcp.tool()
async def get_yields(ctx: Context[ServerSession, Civ7Context], player_id: int = -1) -> str:
    """Per-turn net yields for a player or all majors (requires a game).

    Net food/production/gold/science/culture/happiness/diplomacy per turn
    plus gold balance. The 'is my economy broken?' one-call answer.

    Args:
        player_id: A player id, or -1 (default) for every alive major.
    """
    return await _run_js(ctx, game_tools.get_yields_js(player_id))


@mcp.tool()
async def get_city_production(ctx: Context[ServerSession, Civ7Context], player_id: int = -1) -> str:
    """Every city's production queue for a player or all majors (requires a game).

    Per city: current item (resolved to CONSTRUCTIBLE/UNIT/PROJECT type),
    turns left, and the queued items.

    Args:
        player_id: A player id, or -1 (default) for every alive major.
    """
    return await _run_js(ctx, game_tools.get_city_production_js(player_id))


@mcp.tool()
async def get_wonders(ctx: Context[ServerSession, Civ7Context]) -> str:
    """All built wonders and natural wonders (requires a loaded game).

    Built: wonder type, localized name, city, owner, location, completion.
    Natural: feature type with its tiles (from a full map scan).
    """
    return await _run_js(ctx, game_tools.GET_WONDERS_JS)


@mcp.tool()
async def get_religion(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Religion state for every major (requires a loaded game).

    Pantheons, founded religion (name, beliefs), holy city, and the
    majority religion across each player's cities.
    """
    return await _run_js(ctx, game_tools.GET_RELIGION_JS)


@mcp.tool()
async def get_trade_routes(ctx: Context[ServerSession, Civ7Context], player_id: int = -1) -> str:
    """Active trade routes for a player or all majors (requires a game).

    Per route: endpoint city names + owners, domain, imported resources,
    and export yields.

    Args:
        player_id: A player id, or -1 (default) for every alive major.
    """
    return await _run_js(ctx, game_tools.get_trade_routes_js(player_id))


@mcp.tool()
async def get_notifications(ctx: Context[ServerSession, Civ7Context], player_id: int = 0) -> str:
    """Pending notifications / turn blockers for a player (requires a game).

    Per notification: type, localized message/summary, severity, and
    whether it blocks turn advancement — answers 'why can't the turn end?'.

    Args:
        player_id: Player to inspect (default 0).
    """
    return await _run_js(ctx, game_tools.get_notifications_js(player_id))


@mcp.tool()
async def get_milestones(ctx: Context[ServerSession, Civ7Context], player_id: int = -1) -> str:
    """Age-progression milestones + per-player legacy scores (requires a game).

    Every milestone (legacy path, required points, final flag, complete?)
    plus each player's completed paths and per-path scores.

    Args:
        player_id: A player id, or -1 (default) for every alive major.
    """
    return await _run_js(ctx, game_tools.get_milestones_js(player_id))


@mcp.tool()
async def search_api(ctx: Context[ServerSession, Civ7Context], object_expr: str, pattern: str) -> str:
    """Live API introspection: find members of a game object by regex.

    Walks the prototype chain of the evaluated expression and lists members
    matching the (case-insensitive) pattern with kind/arity. Examples:
    search_api("Players.get(0)", "trade"), search_api("Game", "^get").
    See test-harness/api-crawling.md for validation rules.
    """
    return await _run_js(ctx, game_tools.search_api_js(object_expr, pattern))


@mcp.tool()
async def autoplay(
    ctx: Context[ServerSession, Civ7Context],
    action: str = "start",
    turns: int = 10,
    observe_as: int = 0,
) -> str:
    """Start or stop AI autoplay — the safe fast-forward (requires a game).

    Uses the FireTuner Autoplay recipe verified in
    test-harness/game-api-testing.md. Control returns to `observe_as` after
    `turns` turns. MUTATES GAME STATE: the AI plays those turns for real.

    Args:
        action: "start" (default) or "stop".
        turns: Number of turns to autoplay (start only).
        observe_as: Player to observe as and return control to (start only).
    """
    if action not in ("start", "stop"):
        return "ERROR: action must be 'start' or 'stop'"
    return await _run_js(ctx, game_tools.autoplay_js(action, turns, observe_as))


@mcp.tool()
async def end_turn(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Request end of the current player's turn (requires a loaded game).

    Sends GameContext.sendTurnComplete(). The turn advances asynchronously
    and can be blocked by pending choices/unmoved units — check
    get_notifications for blockers and re-read Game.turn to confirm.
    MUTATES GAME STATE.
    """
    return await _run_js(ctx, game_tools.END_TURN_JS)


@mcp.tool()
async def look_at(ctx: Context[ServerSession, Civ7Context], x: int, y: int) -> str:
    """Point the game camera at a plot (requires a loaded game).

    Camera.lookAtPlot wrapper — frame a location before screenshot().
    """
    return await _run_js(ctx, game_tools.look_at_js(x, y))


@mcp.tool()
async def execute_js_file(ctx: Context[ServerSession, Civ7Context], path: str) -> str:
    """Run a JavaScript file from disk on the debug console.

    Reads the file and executes its contents like execute_js — for running
    real test suites (e.g. mapgen-test-suite.js) without pasting them.

    Args:
        path: Path to a .js file on this machine.
    """
    p = Path(path)
    if not p.is_file():
        return f"ERROR: no such file: {path}"
    try:
        code = p.read_text(encoding="utf-8")
    except OSError as e:
        return f"ERROR: could not read {path}: {e}"
    return await _run_js(ctx, code)


@mcp.tool()
async def reload_ui(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Hot-reload the game's UI (UI.reloadUI()).

    Re-fetches UI documents, JS, and CSS — the no-restart mod iteration
    loop. Database/module-cache changes still need a full game restart.
    """
    return await _run_js(ctx, game_tools.RELOAD_UI_JS)


@mcp.tool()
async def preflight_mod(ctx: Context[ServerSession, Civ7Context], module_path: str) -> str:
    """Validate a mod module's import graph without launching a game.

    Dynamic-imports the module with a cache-buster (the debugging.md
    preflight): catches broken imports in seconds where game logs stay
    silent. Returns ok + export names, or the import error.

    Args:
        module_path: Game-relative module URL, e.g.
            "fs://game/ContinentsPlusPlus/modules/maps/continents-plus-plus.js".
    """
    kick = await _run_js(ctx, game_tools.preflight_mod_js_start(module_path))
    if kick.startswith("ERROR:"):
        return kick
    for _ in range(20):
        await asyncio.sleep(0.25)
        result = await _run_js(ctx, game_tools.PREFLIGHT_MOD_POLL_JS)
        if '"done":true' in result.replace(" ", ""):
            return result
    return f"ERROR: preflight did not settle in 5s; last poll: {result}"


@mcp.tool()
async def list_saves() -> str:
    """List the game's save files (newest first) from the Saves directory.

    Filesystem-level: works whether or not the game is running. Shows
    relative path, size, and modification time.
    """
    return await asyncio.to_thread(game_tools.list_saves)


@mcp.tool()
async def read_game_logs(name: str = "", tail_lines: int = 100, grep: str = "") -> str:
    """Read the game's own log files for failure diagnosis.

    Call with no arguments to list available logs. Key logs: Scripting.log
    (map-gen scripts + console.log output), Database.log (XML errors),
    Modding.log (mod activation), UI.log (shell UI errors). See
    test-harness/debugging.md for the diagnosis workflow.

    Args:
        name: Log filename, e.g. "Scripting.log". Empty = list all logs.
        tail_lines: How many lines from the end to return (default 100).
        grep: Optional case-insensitive substring filter, applied before tailing.
    """
    return await asyncio.to_thread(game_tools.read_log, name, tail_lines, grep)


@mcp.tool()
async def render_map(
    ctx: Context[ServerSession, Civ7Context],
    save_path: str = "",
    tile_px: int = 12,
) -> Image:
    """Render the current game map as an image from exact tile data.

    Unlike screenshot(), this draws what the ENGINE reports per tile:
    terrain/biome colors, tile-owner outlines, cities (circles, white ring,
    larger = capital), and units (triangles), with a player color legend.
    Requires a loaded game.

    Args:
        save_path: Optional file path to also save the PNG to disk.
        tile_px: Pixels per tile (default 12; larger = more readable labels).
    """
    import json as _json

    raw = await _run_js(ctx, game_tools.MAP_DUMP_JS)
    if raw.startswith("ERROR:"):
        raise RuntimeError(raw)
    try:
        dump = _json.loads(raw)
    except _json.JSONDecodeError:
        raise RuntimeError(f"Unexpected map dump response: {raw[:200]}")
    if "error" in dump:
        raise RuntimeError(f"render_map: {dump['error']}")

    png = await asyncio.to_thread(game_tools.render_map_png, dump, tile_px)
    if save_path:
        Path(save_path).write_bytes(png)
    return Image(data=png, format="png")


# Locate API_LIBRARY.md relative to the project root
_api_library_path = Path(__file__).resolve().parent.parent / "API_LIBRARY.md"


@mcp.resource("civ7://api-library")
async def get_api_library() -> str:
    """Full Civ7 JavaScript API reference — all known methods, properties, and patterns."""
    if _api_library_path.is_file():
        return _api_library_path.read_text(encoding="utf-8")
    return "ERROR: API_LIBRARY.md not found. Expected at: " + str(_api_library_path)


@mcp.tool()
async def help() -> str:
    """Show available Civ7 API categories and how to use the debug console.

    Returns a quick-reference summary of all known API areas. For full details
    on every method, read the civ7://api-library resource.
    """
    return """=== Civ7 Debug Console — Quick Reference ===

TOOLS:
  execute_js(code)       — Run JavaScript on the Civ7 debug port. Last expression is returned.
  get_game_state()       — Structured JSON snapshot (sections: overview,players,cities,units,map).
  get_screen()           — Current UI screen stack, pressable buttons, open dialogs.
  describe_screen()      — Semantic what-is-displayed summary: labels, composition, context.
  press_button(caption)  — Press a UI button by caption (engine-input pattern).
  render_map()           — Draw the map from exact tile data (terrain, owners, cities, units).
  reveal_map(scope)      — Reveal the whole map (human/all/player id; Firaxis tuner mechanism).
  list_civs_and_units()  — Full roster: every civ with leader, gold, cities, all units + counts.
  get_continents()       — Continents: type/name, tile count, cities + players present on each.
  get_players()          — Major players: civ, leader, team, gold, government, capital, diplomacy.
  get_citystates()       — Independent powers: name, plot, relationships to majors, suzerain bonus.
  get_age()              — Current age, chronology, turn/date, age progression points.
  get_map_resources()    — All map resources by type (counts; optional tile locations).
  get_player_resources() — A player's resources (type, plot, assigned city) or all majors'.
  get_continent_size()   — Continent sizes: tiles, % of land/map, bounding boxes.
  get_tile(x, y)         — Everything about one plot: terrain, feature, owner, city, units, river.
  get_city(x, y)         — Deep city detail: pops, growth, happiness, yields, production, buildings.
  get_units_at(x, y)     — Full unit detail on a plot: moves, damage, promotions, army.
  get_victory_progress() — Victory progress per team + legacy paths/scores per player.
  get_diplomacy()        — Full matrix: met, wars (names), relationship levels.
  get_tech_civics(id)    — Tech + civic trees: researching, turns left, completed nodes.
  get_yields(id?)        — Net per-turn yields (food/prod/gold/sci/culture/happiness/diplo).
  get_city_production(id?) — Every city's production + queue, resolved to type names.
  get_wonders()          — Built wonders (city/owner/location) + natural wonders.
  get_religion()         — Pantheons, founded religions, beliefs, holy cities.
  get_trade_routes(id?)  — Active routes: endpoints, imported resources, export yields.
  get_notifications(id?) — Pending notifications and end-turn blockers.
  get_milestones(id?)    — Age milestones (complete?) + per-player legacy scores.
  search_api(obj, pat)   — Live introspection: find members of a game object by regex.
  autoplay(action, ...)  — Start/stop AI autoplay fast-forward (MUTATES game state).
  end_turn()             — Request turn end (async; may be blocked — see get_notifications).
  look_at(x, y)          — Point the camera at a plot (pair with screenshot).
  execute_js_file(path)  — Run a .js file from disk (e.g. a test suite).
  reload_ui()            — Hot-reload UI documents/JS/CSS (no game restart).
  preflight_mod(path)    — Cache-busted dynamic import: catch broken mod imports in seconds.
  list_saves()           — List local save files (Steam Cloud saves have no local dir).
  read_game_logs(name)   — Tail/grep the game's logs (Scripting.log etc). No args = list logs.
  screenshot()           — Capture the game window as an image (OS-level; optional save_path).
  help()                 — This help text.

RESOURCES:
  civ7://status      — Connection status to Civ7.
  civ7://api-library — Full API reference (all methods, properties, patterns).

API CATEGORIES:
  GameplayMap     — Map data, tile queries, terrain, yields, spatial queries (70+ methods)
  Players         — Player collection: get(id), getAliveMajorIds(), isAlive(), grantYield()
  Player instance — Properties: name, civ, isAlive, isHuman. Sub-objects below.
  Player.Cities   — getCities(), getCapital(), findClosest(x,y)
  Player.Units    — getUnits(), getUnitIds(), canEverTrain(type)
  Player.Techs    — getResearching(), getResearched(), getTurnsLeft()
  Player.Culture  — getResearching(), getGovernmentType(), getActiveTraditions()
  Player.Treasury — goldBalance, changeGoldBalance(amount)
  Player.Diplomacy— hasMet(), isAtWarWith(), getRelationshipLevelName()
  Player.Resources— getResources(), getCountImportedResources()
  Player.Trade    — getCurrentTradeRoutes(), countPlayerTradeRoutes()
  Game            — turn, age, maxTurns, getTurnDate()
  Game.Diplomacy  — hasMet(p1,p2), getWarData(p1,p2), getActiveEvents()
  Game.VictoryManager — getVictories(), getVictoryProgress()
  Game.Religion   — hasBeenFounded(), getPlayerFromReligion()
  Game.Combat     — simulateAttackAsync(), getBestDefender(x,y)
  Game.Trade      — getCityRoutes(), findTradeRouteBetween()
  Game.CityStates — hasBeenChosen(), isBonusActive()
  GameContext     — sendTurnComplete(), sendPauseRequest()
  Configuration   — getGame(), getMap(), getPlayer(id)
  UI              — isInGame(), reloadUI(), debugPrint(), setClipboardText()
  GameSetup       — (shell only) findGameParameter(id), setGameParameterValue(id, v)
  UI Automation   — press buttons via 'engine-input' CustomEvent (DOM clicks are ignored)
  WorldBuilder    — startBlock(), endBlock()

QUICK EXAMPLES:
  1+1                                          → 2
  GameplayMap.getGridWidth()                   → map width
  Players.getAliveMajorIds()                   → [0, 1, 2, ...]
  Players.get(0).Treasury.goldBalance          → current gold
  JSON.stringify(Players.get(0).Cities.getCities().map(c => c.name))

TIPS:
  • ALWAYS wrap the last expression in JSON.stringify() — bare numbers/objects
    often return "" or [object Object]
  • Last expression in your code is the return value
  • globalThis persists between calls — use it to collect async/promise results
  • import('fs://game/<mod>/file.js?v=' + Date.now()) — validate a mod module's
    import graph without launching (cache-buster required after redeploys)
  • Use Object.getOwnPropertyNames(obj) to discover new properties
  • Read civ7://api-library for the full reference with all parameters
  • See test-harness/ in this repo for the automated testing & debugging playbook
"""


def main():
    """Entry point for the MCP server."""
    global _host, _port

    parser = argparse.ArgumentParser(description="Civ7 MCP Debug Server")
    parser.add_argument("--host", "-H", default="127.0.0.1", help="Civ7 debug host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=4318, help="Civ7 debug port (default: 4318)")
    parser.add_argument("--transport", "-t", choices=["stdio", "streamable-http"], default="stdio",
                        help="MCP transport (default: stdio)")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP port for streamable-http transport (default: 8080)")
    args = parser.parse_args()

    _host = args.host
    _port = args.port

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.http_port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
