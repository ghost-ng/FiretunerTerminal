"""Session logger for recording terminal sessions."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO


class SessionLoggerError(Exception):
    """Raised when session logging fails."""
    pass


class SessionLogger:
    """
    Logs terminal sessions to timestamped files.

    Creates log files in the format: session_YYYY-MM-DD_HH-MM-SS.log
    Writes incrementally and flushes after each entry.
    """

    def __init__(self, session_dir: str = "./sessions"):
        """
        Initialize the session logger.

        Args:
            session_dir: Directory to store session log files.
        """
        self._session_dir = Path(session_dir)
        self._file: Optional[TextIO] = None
        self._filepath: Optional[Path] = None

    @property
    def filepath(self) -> Optional[Path]:
        """Get the current session log file path."""
        return self._filepath

    def start(self, suffix: str = "") -> Path:
        """
        Start a new session log.

        Creates the session directory if needed and opens a new log file.

        Args:
            suffix: Optional suffix to add to the filename (e.g., "_tab1").

        Returns:
            Path to the created log file.

        Raises:
            SessionLoggerError: If the log file cannot be created.
        """
        try:
            # Ensure session directory exists
            self._session_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"session_{timestamp}{suffix}.log"
            self._filepath = self._session_dir / filename

            # Open file for writing
            self._file = open(self._filepath, "w", encoding="utf-8")

            # Write session header
            self._write_line(f"Session started: {datetime.now().isoformat()}")
            self._write_line("-" * 50)

            return self._filepath

        except OSError as e:
            raise SessionLoggerError(f"Failed to create session log: {e}") from e

    def stop(self) -> None:
        """
        Stop the session log and close the file.

        Writes a session end marker and flushes all data.
        """
        if self._file is not None:
            try:
                self._write_line("-" * 50)
                self._write_line(f"Session ended: {datetime.now().isoformat()}")
                self._file.close()
            except Exception:
                pass  # Ignore errors during close
            finally:
                self._file = None

    def log_command(self, command: str) -> None:
        """
        Log a command sent by the user.

        Args:
            command: The command string.
        """
        if self._file is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        # Handle multiline commands
        lines = command.split("\n")
        for i, line in enumerate(lines):
            if i == 0:
                self._write_line(f"[{timestamp}] > {line}")
            else:
                self._write_line(f"[{timestamp}]   {line}")

    def log_response(self, response: str) -> None:
        """
        Log a response received from the server.

        Args:
            response: The response string.
        """
        if self._file is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        # Handle multiline responses
        lines = response.split("\n")
        for line in lines:
            self._write_line(f"[{timestamp}] {line}")

    def log_error(self, error: str) -> None:
        """
        Log an error message.

        Args:
            error: The error message.
        """
        if self._file is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write_line(f"[{timestamp}] ERROR: {error}")

    def log_info(self, info: str) -> None:
        """
        Log an informational message.

        Args:
            info: The info message.
        """
        if self._file is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write_line(f"[{timestamp}] INFO: {info}")

    def _write_line(self, line: str) -> None:
        """Write a line to the log file and flush."""
        if self._file is not None:
            try:
                self._file.write(line + "\n")
                self._file.flush()
            except Exception:
                pass  # Don't crash on log write failure

    def __enter__(self) -> "SessionLogger":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
