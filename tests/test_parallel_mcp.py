"""Verify concurrent requests through the MCP server / connection layer.

Runs a mock FireTuner server (real binary protocol from civ7_terminal.protocol)
that evaluates a tiny subset of JS (`<n>*<n>` style payloads) and answers
in order received, like the game does. Then:

  1. ConnectionManager level: N concurrent send_command() calls, assert every
     response matches its command.
  2. Full MCP stdio round-trip: spawn `python -m civ7_terminal.mcp_server`
     pointed at the mock, fire N concurrent execute_js tool calls through the
     MCP client SDK, assert every result matches.

Usage:  python tests/test_parallel_mcp.py [--port 43180]
Exit code 0 = all passed.
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import struct  # noqa: E402

from civ7_terminal.protocol import HEADER_SIZE, MESSAGE_TYPE, decode_header, decode_message  # noqa: E402

CMD_RE = re.compile(r"^CMD:\d+:(.*)$", re.DOTALL)
N_PARALLEL = 20


def encode_response(result: str) -> bytes:
    """Encode a response frame the way the game does: [len][type=3][{result}\\0]."""
    payload = result.encode("utf-8") + b"\0"
    return struct.pack("<II", len(payload), MESSAGE_TYPE) + payload


async def mock_firetuner(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Speak the FireTuner protocol; eval `a*b` payloads with varied delay.

    Responses are written in the order commands arrive (matching the game),
    but slow first commands force later commands to queue up behind them,
    which is exactly the window where mismatched futures would surface.
    """
    try:
        first = True
        while True:
            header = await reader.readexactly(HEADER_SIZE)
            length, _ = decode_header(header)
            payload = await reader.readexactly(length)
            js = CMD_RE.match(decode_message(header, payload).payload).group(1)
            if first:
                await asyncio.sleep(0.3)  # let concurrent senders pile up
                first = False
            a, b = js.split("*")
            writer.write(encode_response(str(int(a) * int(b))))
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        writer.close()


async def test_connection_manager(port: int) -> bool:
    from civ7_terminal.connection import ConnectionConfig, ConnectionManager, ConnectionState

    conn = ConnectionManager(ConnectionConfig(host="127.0.0.1", port=port))
    await conn.start()
    for _ in range(50):
        if conn.state == ConnectionState.CONNECTED:
            break
        await asyncio.sleep(0.1)
    else:
        print("FAIL: ConnectionManager never connected to mock")
        return False

    async def one(i: int):
        return i, await conn.send_command(f"{i}*{i}")

    results = await asyncio.gather(*(one(i) for i in range(N_PARALLEL)))
    await conn.stop()

    bad = [(i, r) for i, r in results if r != str(i * i)]
    for i, r in bad:
        print(f"  MISMATCH: command {i}*{i} got {r!r}, expected {i * i}")
    print(f"ConnectionManager: {N_PARALLEL - len(bad)}/{N_PARALLEL} concurrent commands matched")
    return not bad


async def test_mcp_roundtrip(port: int) -> bool:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "civ7_terminal.mcp_server", "--port", str(port)],
        cwd=str(REPO_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await asyncio.sleep(1.0)  # allow server->mock connection

            async def one(i: int):
                res = await session.call_tool("execute_js", {"code": f"{i}*{i}"})
                return i, res.content[0].text

            results = await asyncio.gather(*(one(i) for i in range(N_PARALLEL)))

    bad = [(i, r) for i, r in results if r != str(i * i)]
    for i, r in bad:
        print(f"  MISMATCH: execute_js({i}*{i}) got {r!r}, expected {i * i}")
    print(f"MCP stdio round-trip: {N_PARALLEL - len(bad)}/{N_PARALLEL} concurrent execute_js calls matched")
    return not bad


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=43180)
    args = parser.parse_args()

    server = await asyncio.start_server(mock_firetuner, "127.0.0.1", args.port)
    try:
        ok = await test_connection_manager(args.port)
        ok = await test_mcp_roundtrip(args.port) and ok
    finally:
        server.close()
        await server.wait_closed()

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
