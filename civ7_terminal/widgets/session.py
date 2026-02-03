"""Terminal session widget combining output and input."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget

from ..session_logger import SessionLogger
from .terminal import TerminalOutput


class TerminalSession(Widget):
    """
    A complete terminal session with output, input area, and logging.

    Each session maintains its own:
    - Terminal output history
    - Last response (for copy functionality)
    - Session logger
    """

    DEFAULT_CSS = """
    TerminalSession {
        width: 100%;
        height: 100%;
        layout: vertical;
    }

    TerminalSession > TerminalOutput {
        height: 1fr;
    }
    """

    def __init__(
        self,
        session_id: str,
        session_dir: str,
        tab_suffix: str = "",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._session_id = session_id
        self._session_dir = session_dir
        self._tab_suffix = tab_suffix
        self._last_response: Optional[str] = None
        self._session_logger: Optional[SessionLogger] = None

    def compose(self) -> ComposeResult:
        """Compose the session layout."""
        yield TerminalOutput(id=f"output-{self._session_id}")

    def on_mount(self) -> None:
        """Initialize session logger on mount."""
        self._session_logger = SessionLogger(self._session_dir)
        try:
            log_path = self._session_logger.start(suffix=self._tab_suffix)
            self.terminal.add_info(f"Session log: {log_path}")
        except Exception as e:
            self.terminal.add_error(f"Failed to start session log: {e}")

    def on_unmount(self) -> None:
        """Clean up session logger."""
        if self._session_logger:
            self._session_logger.stop()

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def terminal(self) -> TerminalOutput:
        """Get the terminal output widget."""
        return self.query_one(TerminalOutput)

    @property
    def last_response(self) -> Optional[str]:
        """Get the last response received in this session."""
        return self._last_response

    @property
    def logger(self) -> Optional[SessionLogger]:
        """Get the session logger."""
        return self._session_logger

    def add_response(self, response: str) -> None:
        """Add a response to this session."""
        self._last_response = response
        self.terminal.add_response(response)
        if self._session_logger:
            self._session_logger.log_response(response)

    def add_command(self, command: str) -> None:
        """Add a command to the terminal display."""
        self.terminal.add_command(command)

    def add_info(self, info: str) -> None:
        """Add an info message."""
        self.terminal.add_info(info)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.terminal.add_error(error)
        if self._session_logger:
            self._session_logger.log_error(error)

    def log_command(self, command: str) -> None:
        """Log a command to the session file."""
        if self._session_logger:
            self._session_logger.log_command(command)

    def log_info(self, info: str) -> None:
        """Log an info message to the session file."""
        if self._session_logger:
            self._session_logger.log_info(info)

    def clear(self) -> None:
        """Clear the terminal output."""
        self.terminal.clear()

    def toggle_raw_mode(self) -> bool:
        """Toggle raw output mode."""
        return self.terminal.toggle_raw_mode()
