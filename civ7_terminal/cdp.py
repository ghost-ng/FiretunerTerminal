"""CDP fallback transport for the Civ7 Cohtml UI debugger (port 9444).

The game suspends the FireTuner port (4318) during multiplayer/hotseat
sessions, but the Cohtml UI debugger stays up and evaluates the same JS in
the same context. This module is the minimal Runtime.evaluate client that
ConnectionManager uses as an automatic fallback while the tuner is down.

Each call opens a fresh WebSocket to the first CDP target: connections are
local and cheap, and reconnecting per call self-heals across target changes.
No Runtime.enable handshake is needed; exceptions surface in
exceptionDetails rather than as protocol errors (verified live 2026-08-17).
"""

from __future__ import annotations

import asyncio
import json
import socket
import urllib.request

CDP_PORT = 9444


class CdpError(Exception):
    """Raised when the CDP endpoint is unreachable or misbehaves."""


def is_available(host: str = "127.0.0.1", port: int = CDP_PORT, timeout: float = 0.4) -> bool:
    """Quick TCP check for the CDP port."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _evaluate_sync(js: str, host: str, port: int, timeout: float) -> str:
    import websocket  # lazy: only needed when the fallback actually engages

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/json", timeout=3) as r:
            targets = json.loads(r.read().decode())
    except OSError as e:
        raise CdpError(f"CDP target list unreachable: {e}") from e
    if not targets:
        raise CdpError("CDP endpoint has no debuggable targets")

    ws_url = targets[0]["webSocketDebuggerUrl"]
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
    except (OSError, websocket.WebSocketException) as e:
        raise CdpError(f"CDP WebSocket connect failed: {e}") from e
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": js, "returnByValue": True},
        }))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") != 1:
                continue  # unsolicited event
            if "error" in msg:
                raise CdpError(f"CDP protocol error: {msg['error']}")
            result = msg.get("result", {})
            exc = result.get("exceptionDetails")
            if exc:
                # The tuner-parity wrapper catches JS errors itself, so this
                # only fires for syntax-level failures — report like the
                # tuner would (as text), not as a transport failure.
                desc = exc.get("exception", {}).get("description") or exc.get("text", "")
                return desc or "CDP evaluation failed"
            value = result.get("result", {}).get("value")
            return "" if value is None else str(value)
    except (OSError, websocket.WebSocketException) as e:
        raise CdpError(f"CDP WebSocket error: {e}") from e
    finally:
        ws.close()


async def evaluate(js: str, host: str = "127.0.0.1", port: int = CDP_PORT,
                   timeout: float = 30.0) -> str:
    """Evaluate a JS expression over CDP and return its stringified value.

    Raises CdpError when the endpoint is unreachable or the protocol fails.
    """
    return await asyncio.to_thread(_evaluate_sync, js, host, port, timeout)
