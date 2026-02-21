"""MCP server for Civ7 debug console - allows AI agents to execute JavaScript commands."""

import argparse
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

from .connection import ConnectionConfig, ConnectionManager, ConnectionState


@dataclass
class Civ7Context:
    """Lifespan context holding the connection to Civ7."""
    connection: ConnectionManager


@asynccontextmanager
async def civ7_lifespan(server: FastMCP) -> AsyncIterator[Civ7Context]:
    """Manage Civ7 connection lifecycle."""
    config = ConnectionConfig(host=_host, port=_port)
    connection = ConnectionManager(config)
    await connection.start()
    try:
        yield Civ7Context(connection=connection)
    finally:
        await connection.stop()


# Module-level config set by main() before server starts
_host = "127.0.0.1"
_port = 4318

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

    if connection.state == ConnectionState.DISCONNECTED:
        return "ERROR: Not connected to Civ7 debug port. Is the game running with FireTuner enabled?"

    response = await connection.send_command(code)

    if response is None:
        return "ERROR: Command timed out or connection lost."

    return response


@mcp.resource("civ7://status")
async def get_status(ctx: Context[ServerSession, Civ7Context]) -> str:
    """Get current connection status to the Civ7 debug port."""
    connection = ctx.request_context.lifespan_context.connection
    state = connection.state

    if state == ConnectionState.CONNECTED:
        return f"Connected to Civ7 at {_host}:{_port}"
    elif state == ConnectionState.CONNECTING:
        return f"Connecting to Civ7 at {_host}:{_port}..."
    else:
        return f"Disconnected from Civ7 ({_host}:{_port}). Waiting to reconnect..."


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
  execute_js(code)  — Run JavaScript on the Civ7 debug port. Last expression is returned.
  help()            — This help text.

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
  UI              — isInGame(), debugPrint(), setClipboardText()
  WorldBuilder    — startBlock(), endBlock()

QUICK EXAMPLES:
  1+1                                          → 2
  GameplayMap.getGridWidth()                   → map width
  Players.getAliveMajorIds()                   → [0, 1, 2, ...]
  Players.get(0).Treasury.goldBalance          → current gold
  JSON.stringify(Players.get(0).Cities.getCities().map(c => c.name))

TIPS:
  • Use JSON.stringify() for complex objects — raw objects return [object Object]
  • Last expression in your code is the return value
  • Use Object.getOwnPropertyNames(obj) to discover new properties
  • Read civ7://api-library for the full reference with all parameters
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
