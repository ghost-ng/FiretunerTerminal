"""Status bar widget showing connection state."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..connection import ConnectionState


class StatusBar(Widget):
    """
    Status bar showing connection state and host info.

    Displays:
    - Application title
    - Connection status indicator (colored dot)
    - Host:port info
    - Retry countdown when disconnected
    """

    DEFAULT_CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text;
    }

    StatusBar .title {
        width: auto;
        padding: 0 1;
        text-style: bold;
    }

    StatusBar .spacer {
        width: 1fr;
    }

    StatusBar .status {
        width: auto;
        padding: 0 1;
    }

    StatusBar .status-connected {
        color: $success;
    }

    StatusBar .status-disconnected {
        color: $error;
    }

    StatusBar .status-connecting {
        color: $warning;
    }

    StatusBar .host-info {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }
    """

    state: reactive[ConnectionState] = reactive(ConnectionState.DISCONNECTED)
    retry_countdown: reactive[float | None] = reactive(None)
    host: reactive[str] = reactive("127.0.0.1")
    port: reactive[int] = reactive(4318)

    def compose(self) -> ComposeResult:
        """Compose the status bar layout."""
        yield Static("Civ7 Debug Terminal", classes="title")
        yield Static("", classes="spacer")
        yield Static("", id="status", classes="status")
        yield Static("", id="host-info", classes="host-info")

    def on_mount(self) -> None:
        """Update display on mount."""
        self._update_status()
        self._update_host_info()

    def watch_state(self, state: ConnectionState) -> None:
        """React to state changes."""
        self._update_status()

    def watch_retry_countdown(self, countdown: float | None) -> None:
        """React to retry countdown changes."""
        self._update_status()

    def watch_host(self, host: str) -> None:
        """React to host changes."""
        self._update_host_info()

    def watch_port(self, port: int) -> None:
        """React to port changes."""
        self._update_host_info()

    def _update_status(self) -> None:
        """Update the status indicator."""
        status_widget = self.query_one("#status", Static)

        if self.state == ConnectionState.CONNECTED:
            status_widget.update("[●]")
            status_widget.set_classes("status status-connected")
        elif self.state == ConnectionState.CONNECTING:
            status_widget.update("[◐]")
            status_widget.set_classes("status status-connecting")
        else:
            if self.retry_countdown is not None and self.retry_countdown > 0:
                status_widget.update(f"[○] retry in {int(self.retry_countdown)}s")
            else:
                status_widget.update("[○]")
            status_widget.set_classes("status status-disconnected")

    def _update_host_info(self) -> None:
        """Update the host info display."""
        host_widget = self.query_one("#host-info", Static)
        host_widget.update(f"{self.host}:{self.port}")

    def set_connection_state(
        self,
        state: ConnectionState,
        retry_countdown: float | None = None,
    ) -> None:
        """
        Update the connection state display.

        Args:
            state: The new connection state.
            retry_countdown: Seconds until retry (for disconnected state).
        """
        self.state = state
        self.retry_countdown = retry_countdown

    def set_host_info(self, host: str, port: int) -> None:
        """
        Update the host info display.

        Args:
            host: The host address.
            port: The port number.
        """
        self.host = host
        self.port = port
