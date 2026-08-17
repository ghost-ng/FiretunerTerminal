"""MCP server for Civ7 debug console - allows AI agents to execute JavaScript commands."""

import argparse
import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.session import ServerSession

from .connection import ConnectionConfig, ConnectionManager, ConnectionState
from .screenshot import ScreenshotError, capture_game_window
from . import game_tools


@dataclass
class Civ7Context:
    """Lifespan context holding the connection to Civ7."""
    connection: ConnectionManager


@asynccontextmanager
async def civ7_lifespan(server: FastMCP) -> AsyncIterator[Civ7Context]:
    """Manage Civ7 connection lifecycle."""
    global _connection
    config = ConnectionConfig(host=_host, port=_port)
    connection = ConnectionManager(config)
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
    connection = ctx.request_context.lifespan_context.connection

    if connection.state != ConnectionState.CONNECTED:
        diagnosis = await asyncio.to_thread(game_tools.diagnose_disconnect, _port)
        return f"ERROR: Not connected to Civ7 debug port. Diagnosis: {diagnosis}"

    response = await connection.send_command(code)

    if response is None:
        return "ERROR: Command timed out or connection lost."

    return response


async def _run_js(ctx: Context[ServerSession, Civ7Context], code: str) -> str:
    """Internal: run JS through the shared connection with the same error text."""
    return await execute_js(code, ctx)


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
        return f"Connected to Civ7 at {_host}:{_port}"
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
  press_button(caption)  — Press a UI button by caption (engine-input pattern).
  render_map()           — Draw the map from exact tile data (terrain, owners, cities, units).
  reveal_map(scope)      — Reveal the whole map (human/all/player id; Firaxis tuner mechanism).
  list_civs_and_units()  — Full roster: every civ with leader, gold, cities, all units + counts.
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
