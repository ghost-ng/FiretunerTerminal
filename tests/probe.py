"""Reusable synchronous probe for the Civ7 debug port.

Sends a single JavaScript expression and prints the result. Used by the
walkthroughs in this folder and handy for quick one-off queries without
launching the full terminal UI.

Usage:
    python tests/probe.py 'GameplayMap.getGridWidth()'
    python tests/probe.py 'typeof Players'
    python tests/probe.py --host 127.0.0.1 --port 4318 'UI.isInShell()'

Import as a module for scripted probing:
    from tests.probe import Probe
    with Probe() as p:
        print(p.send('1+1'))
"""

import argparse
import socket
import sys
from pathlib import Path

# Allow running from the repo root or from inside tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from civ7_terminal import protocol


class Probe:
    """Minimal synchronous client for the Civ7 debug port."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4318, timeout: float = 15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=5)

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def __enter__(self) -> "Probe":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _recv_exact(self, n: int) -> bytes:
        assert self.sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed by game")
            buf += chunk
        return buf

    def send(self, js: str) -> str:
        """Send a JavaScript expression, return the game's response string."""
        assert self.sock is not None, "call connect() first"
        self.sock.sendall(protocol.encode_command(js))
        self.sock.settimeout(self.timeout)
        header = self._recv_exact(protocol.HEADER_SIZE)
        length, _msg_type = protocol.decode_header(header)
        payload = self._recv_exact(length)
        return protocol.decode_payload(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one JS expression to the Civ7 debug port")
    parser.add_argument("js", help="JavaScript expression to evaluate")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4318)
    args = parser.parse_args()

    with Probe(args.host, args.port) as p:
        print(p.send(args.js))


if __name__ == "__main__":
    main()
