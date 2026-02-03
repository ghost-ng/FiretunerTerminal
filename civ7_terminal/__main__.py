"""Entry point for the Civ7 Debug Terminal."""

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="civ7-terminal",
        description="Debug terminal for Civilization 7",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="127.0.0.1",
        help="Debug server host address",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=4318,
        help="Debug server port",
    )

    parser.add_argument(
        "--session-dir",
        "-s",
        type=str,
        default="./sessions",
        help="Directory for session log files",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser.parse_args()


def ensure_session_dir(session_dir: str) -> None:
    """Ensure the session directory exists."""
    path = Path(session_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Cannot create session directory '{session_dir}': {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Validate port
    if not 1 <= args.port <= 65535:
        print(f"Error: Port must be between 1 and 65535, got {args.port}", file=sys.stderr)
        sys.exit(1)

    # Ensure session directory exists
    ensure_session_dir(args.session_dir)

    # Import app here to avoid slow startup for --help/--version
    from .app import Civ7TerminalApp

    # Create and run the app
    app = Civ7TerminalApp(
        host=args.host,
        port=args.port,
        session_dir=args.session_dir,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C during startup
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
