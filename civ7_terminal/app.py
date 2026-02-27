"""Main Textual application for Civ7 Debug Terminal."""

from typing import Optional

import pyperclip
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import Click, Key
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static, Tab, TabbedContent, TabPane, TextArea

from .completions import CompletionEngine
from .connection import ConnectionConfig, ConnectionManager, ConnectionState
from .widgets import StatusBar, TerminalSession


class RenameTabScreen(ModalScreen):
    """Modal screen for renaming a tab."""

    DEFAULT_CSS = """
    RenameTabScreen {
        align: center middle;
    }

    RenameTabScreen > Vertical {
        width: 40;
        height: auto;
        background: $boost;
        border: solid $primary;
        padding: 1;
    }

    RenameTabScreen Static {
        width: 100%;
        margin-bottom: 1;
    }

    RenameTabScreen Input {
        width: 100%;
        margin-bottom: 1;
    }

    RenameTabScreen Button {
        width: 100%;
        background: $boost;
        color: $text;
        margin: 0 0 1 0;
    }

    RenameTabScreen Button:hover {
        background: $primary;
    }

    RenameTabScreen Button#cancel {
        margin-bottom: 0;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, current_name: str, tab_id: str):
        super().__init__()
        self._current_name = current_name
        self._tab_id = tab_id

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Rename Tab")
            yield Input(value=self._current_name, id="new-name")
            yield Button("Rename", id="rename")
            yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter in input."""
        self._do_rename()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "rename":
            self._do_rename()
        else:
            self.dismiss(None)

    def _do_rename(self) -> None:
        """Perform the rename."""
        new_name = self.query_one(Input).value.strip()
        if new_name:
            self.dismiss((self._tab_id, new_name))
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel the rename."""
        self.dismiss(None)


class CommandInput(TextArea):
    """Multiline input widget with history support."""

    DEFAULT_CSS = """
    CommandInput {
        dock: bottom;
        width: 100%;
        height: auto;
        min-height: 3;
        max-height: 7;
        border: solid $primary;
        padding: 0;
        background: $surface;
        color: #00ffff;
    }

    CommandInput:focus {
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("tab", "complete", "Complete", show=False, priority=True),
        Binding("up", "history_up", "History Up", show=False, priority=True),
        Binding("down", "history_down", "History Down", show=False, priority=True),
        Binding("enter", "submit", "Submit", show=False, priority=True),
        Binding("ctrl+enter", "newline", "Newline", show=False, priority=True),
        Binding("ctrl+j", "newline", "Newline", show=False, priority=True),
        Binding("ctrl+a", "select_all", "Select All", show=False, priority=True),
    ]

    def action_select_all(self) -> None:
        """Select all text in the input."""
        self.select_all()

    def _is_syntax_complete(self, text: str) -> bool:
        """Check if JavaScript syntax is complete (balanced brackets/quotes)."""
        # Track bracket counts and string state
        paren_count = 0  # ()
        brace_count = 0  # {}
        bracket_count = 0  # []
        in_string = None  # None, '"', "'", or '`'
        escape_next = False

        for char in text:
            # Handle escape sequences in strings
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            # Handle string delimiters
            if char in ('"', "'", '`'):
                if in_string is None:
                    in_string = char
                elif in_string == char:
                    in_string = None
                continue

            # Skip bracket counting if inside a string
            if in_string:
                continue

            # Count brackets
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1

        # Syntax is complete if all brackets balanced and not in a string
        return (
            paren_count == 0
            and brace_count == 0
            and bracket_count == 0
            and in_string is None
        )

    def action_submit(self) -> None:
        """Submit the current input, or continue if syntax incomplete."""
        self._reset_completion_state()
        text = self.text.strip()

        # Empty input - just submit
        if not text:
            self.post_message(self.Submitted(self.text))
            return

        # Check if syntax is complete
        if self._is_syntax_complete(text):
            self.post_message(self.Submitted(self.text))
        else:
            # Incomplete syntax - add newline for continuation (max 5 lines)
            if self.document.line_count < 5:
                self.insert("\n")

    def action_newline(self) -> None:
        """Insert a newline (max 5 lines)."""
        self._reset_completion_state()
        if self.document.line_count < 5:
            self.insert("\n")

    class Submitted(Message):
        """Message sent when input is submitted."""
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._current_input: str = ""
        # Tab-completion state
        self._completions: list[str] = []
        self._completion_index: int = -1
        self._completion_prefix: str = ""
        self._completion_start: int = -1
        self._completion_engine: Optional[CompletionEngine] = None

    def set_completion_engine(self, engine: CompletionEngine) -> None:
        """Attach a CompletionEngine for tab completion."""
        self._completion_engine = engine

    @property
    def value(self) -> str:
        """Get the current text."""
        return self.text

    @value.setter
    def value(self, text: str) -> None:
        """Set the current text."""
        self.load_text(text)

    def _reset_completion_state(self) -> None:
        """Clear any in-progress tab completion cycle."""
        self._completions = []
        self._completion_index = -1
        self._completion_prefix = ""
        self._completion_start = -1

    def _calc_flat_offset(self) -> int:
        """Return the cursor position as a flat character offset into self.text."""
        row, col = self.cursor_location
        offset = 0
        for i, line in enumerate(self.text.split("\n")):
            if i == row:
                offset += col
                break
            offset += len(line) + 1  # +1 for the newline
        return offset

    def _get_current_partial(self) -> str:
        """Extract the text after the last dot before cursor (the partial member name).

        If the token has no dot, returns the whole token.
        """
        offset = self._calc_flat_offset()
        if self._completion_engine is None:
            return ""
        token = self._completion_engine._extract_token(self.text, offset)
        if "." in token:
            return token.rsplit(".", 1)[1]
        return token

    def action_complete(self) -> None:
        """Handle Tab: start or cycle through completions."""
        if self._completion_engine is None or not self._completion_engine.is_loaded:
            return

        if self._completions and self._completion_index >= 0:
            # Already cycling -- advance to next candidate
            self._completion_index = (self._completion_index + 1) % len(self._completions)
            self._apply_completion()
            return

        # Start a new completion
        offset = self._calc_flat_offset()
        candidates = self._completion_engine.get_completions(self.text, offset)
        if not candidates:
            return

        self._completion_prefix = self._get_current_partial()
        self._completion_start = offset - len(self._completion_prefix)
        self._completions = candidates
        self._completion_index = 0
        self._apply_completion()

    def _apply_completion(self) -> None:
        """Replace the current partial token with the selected completion.

        Uses ``_completion_start`` so that cycling works correctly -- each
        successive Tab replaces from the same start position regardless of
        the length of the previously inserted candidate.
        """
        if not self._completions or self._completion_index < 0:
            return

        chosen = self._completions[self._completion_index]
        start = self._completion_start
        offset = self._calc_flat_offset()

        full_text = self.text
        new_text = full_text[:start] + chosen + full_text[offset:]
        new_cursor_offset = start + len(chosen)

        self.load_text(new_text)

        # Reposition cursor
        pos = 0
        for row_idx, line in enumerate(new_text.split("\n")):
            if pos + len(line) >= new_cursor_offset:
                col_idx = new_cursor_offset - pos
                self.move_cursor((row_idx, col_idx))
                break
            pos += len(line) + 1  # +1 for newline

    def on_key(self, event: Key) -> None:
        """Reset completion state on any non-Tab key."""
        if event.key != "tab":
            self._reset_completion_state()

    def add_to_history(self, command: str) -> None:
        """Add a command to history."""
        if command.strip() and (not self._history or self._history[-1] != command):
            self._history.append(command)
        self._history_index = -1
        self._current_input = ""

    def action_history_up(self) -> None:
        """Navigate to previous command in history."""
        self._reset_completion_state()
        # Only navigate history if cursor is on first line
        cursor_row = self.cursor_location[0]
        if cursor_row > 0:
            # Let default behavior handle cursor movement
            self.action_cursor_up()
            return

        if not self._history:
            return

        if self._history_index == -1:
            self._current_input = self.text
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1

        self.load_text(self._history[self._history_index])
        self.action_cursor_line_end()

    def action_history_down(self) -> None:
        """Navigate to next command in history."""
        self._reset_completion_state()
        # Only navigate history if cursor is on last line
        cursor_row = self.cursor_location[0]
        last_row = self.document.line_count - 1
        if cursor_row < last_row:
            # Let default behavior handle cursor movement
            self.action_cursor_down()
            return

        if self._history_index == -1:
            return

        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.load_text(self._history[self._history_index])
        else:
            self._history_index = -1
            self.load_text(self._current_input)

        self.action_cursor_line_end()

    def clear_input(self) -> None:
        """Clear the current input."""
        self.load_text("")
        self._history_index = -1
        self._current_input = ""
        self._reset_completion_state()


class Civ7TerminalApp(App):
    """Main Civ7 Debug Terminal application."""

    TITLE = "Civ7 Debug Terminal"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
        height: 1fr;
    }

    ContentSwitcher {
        height: 1fr;
    }

    TerminalSession {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear_screen", "Clear", show=False),
        Binding("pageup", "scroll_up", "Scroll Up", show=False),
        Binding("pagedown", "scroll_down", "Scroll Down", show=False),
        Binding("ctrl+c", "cancel_input", "Cancel", show=False),
        Binding("ctrl+shift+c", "copy_last_response", "Copy", show=False),
        Binding("ctrl+t", "new_tab", "New Tab", show=False),
        Binding("ctrl+w", "close_tab", "Close Tab", show=False),
        Binding("ctrl+tab", "next_tab", "Next Tab", show=False),
        Binding("ctrl+shift+tab", "prev_tab", "Previous Tab", show=False),
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4318,
        session_dir: str = "./sessions",
    ):
        super().__init__()
        self._host = host
        self._port = port
        self._session_dir = session_dir

        self._connection: Optional[ConnectionManager] = None
        self._tab_counter: int = 0
        self._pending_tab_id: Optional[str] = None  # Tab awaiting response
        self._ever_connected: bool = False  # Track if we've connected at least once
        self._showed_connecting_msg: bool = False  # Avoid spamming connecting messages

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield StatusBar()
        with Container(id="main-container"):
            with TabbedContent(id="tabs"):
                # Create first tab
                self._tab_counter += 1
                tab_id = f"session-{self._tab_counter}"
                with TabPane(f"Session {self._tab_counter}", id=tab_id):
                    yield TerminalSession(
                        session_id=tab_id,
                        session_dir=self._session_dir,
                        tab_suffix=f"_tab{self._tab_counter}",
                        id=f"terminal-{tab_id}",
                    )
        yield CommandInput(id="command-input")

    async def on_mount(self) -> None:
        """Initialize on mount."""
        # Set up status bar
        status_bar = self.query_one(StatusBar)
        status_bar.set_host_info(self._host, self._port)

        # Set up connection manager
        config = ConnectionConfig(host=self._host, port=self._port)
        self._connection = ConnectionManager(
            config=config,
            on_state_change=self._on_connection_state_change,
            on_response=self._on_response,
            on_error=self._on_connection_error,
        )

        # Start connection
        await self._connection.start()

        # Load completions engine
        from pathlib import Path as _Path

        completions_path = _Path(__file__).resolve().parent.parent / "completions.json"
        engine = CompletionEngine()
        if engine.load(completions_path):
            self.query_one(CommandInput).set_completion_engine(engine)

        # Focus on input
        self.query_one(CommandInput).focus()

        # Show help hint in first tab
        session = self._get_active_session()
        if session:
            session.add_info("Type /help for available commands")

    def _get_active_session(self) -> Optional[TerminalSession]:
        """Get the currently active terminal session."""
        try:
            tabs = self.query_one(TabbedContent)
            active_tab_id = tabs.active
            if active_tab_id:
                return self.query_one(f"#terminal-{active_tab_id}", TerminalSession)
        except Exception:
            pass
        return None

    def _get_session_by_id(self, tab_id: str) -> Optional[TerminalSession]:
        """Get a terminal session by its tab ID."""
        try:
            return self.query_one(f"#terminal-{tab_id}", TerminalSession)
        except Exception:
            return None

    def on_click(self, event: Click) -> None:
        """Handle mouse clicks for tab rename."""
        # Right-click (button 3) on tab to rename
        if event.button == 3:
            widget = event.widget
            # Walk up the widget tree to find a Tab
            while widget is not None:
                if isinstance(widget, Tab):
                    self._show_rename_tab_screen(widget)
                    return
                widget = widget.parent

    def _show_rename_tab_screen(self, tab: Tab) -> None:
        """Show the rename tab screen."""
        # Get the tab pane ID from the tab
        tab_id = tab.id
        if tab_id and tab_id.startswith("--content-tab-"):
            # Extract the actual pane ID
            pane_id = tab_id.replace("--content-tab-", "")
        else:
            pane_id = tab_id

        current_name = tab.label.plain if hasattr(tab.label, 'plain') else str(tab.label)

        def handle_result(result) -> None:
            if result:
                tab_id, new_name = result
                self._rename_tab(tab_id, new_name)

        self.push_screen(RenameTabScreen(current_name, pane_id), handle_result)

    def _rename_tab(self, tab_id: str, new_name: str) -> None:
        """Rename a tab."""
        try:
            tabs = self.query_one(TabbedContent)
            # Find the tab and update its label
            for tab in tabs.query(Tab):
                # Match by the pane ID in the tab's ID
                if tab.id and tab_id in tab.id:
                    tab.label = new_name
                    break
        except Exception:
            pass

    async def on_unmount(self) -> None:
        """Clean up on unmount."""
        if self._connection:
            await self._connection.stop()

    def _on_connection_state_change(
        self,
        state: ConnectionState,
        retry_countdown: Optional[float],
    ) -> None:
        """Handle connection state changes."""
        try:
            status_bar = self.query_one(StatusBar)
            status_bar.set_connection_state(state, retry_countdown)
        except Exception:
            pass  # Widget not available yet

        # Show connection status in active session (avoid spamming)
        session = self._get_active_session()
        if session:
            try:
                if state == ConnectionState.CONNECTED:
                    self._ever_connected = True
                    self._showed_connecting_msg = False
                    session.add_info(f"Connected to {self._host}:{self._port}")
                    session.log_info(f"Connected to {self._host}:{self._port}")
                elif state == ConnectionState.CONNECTING:
                    # Only show "Connecting..." once, not on every retry
                    if not self._showed_connecting_msg:
                        self._showed_connecting_msg = True
                        session.add_info(f"Connecting to {self._host}:{self._port}...")
                    session.log_info(f"Connecting to {self._host}:{self._port}...")
                elif state == ConnectionState.DISCONNECTED:
                    # Only show disconnect message if we were previously connected
                    if self._ever_connected and not self._showed_connecting_msg:
                        self._showed_connecting_msg = True  # Reuse flag to prevent spam
                        session.add_info("Disconnected. Reconnecting...")
                    session.log_info("Disconnected")
            except Exception:
                pass

    def _on_response(self, response: str) -> None:
        """Handle received response."""
        # Route response to the tab that sent the command
        target_tab_id = self._pending_tab_id
        if target_tab_id:
            session = self._get_session_by_id(target_tab_id)
            if session:
                session.add_response(response)
                return

        # Fallback to active session
        session = self._get_active_session()
        if session:
            session.add_response(response)

    def _on_connection_error(self, error: str) -> None:
        """Handle connection errors."""
        # Only show connection errors after we've been connected at least once
        # This prevents spam during initial connection attempts when the game isn't running
        if self._ever_connected:
            session = self._get_active_session()
            if session:
                session.add_error(error)

    async def on_command_input_submitted(self, event: CommandInput.Submitted) -> None:
        """Handle command input submission."""
        command_input = self.query_one(CommandInput)
        command = event.value.strip()

        if not command:
            return

        # Add to history
        command_input.add_to_history(command)
        command_input.clear_input()

        # Handle built-in commands (first line only for multiline)
        # But not comments starting with // or #
        first_line = command.split("\n")[0].strip()
        if first_line.startswith("/") and not first_line.startswith("//"):
            await self._handle_builtin_command(first_line)
            return

        # Send command
        await self._send_command(command)

    async def _send_command(self, command: str) -> None:
        """Send a command to the debug port, filtering out comments."""
        session = self._get_active_session()
        if not session:
            return

        # Track which tab sent this command for response routing
        tabs = self.query_one(TabbedContent)
        self._pending_tab_id = tabs.active

        # Split into lines and process
        lines = command.split("\n")
        code_lines = []

        for line in lines:
            stripped = line.strip()
            # Check if line is a comment
            if stripped.startswith("//") or stripped.startswith("#"):
                # Echo comment to terminal but don't send
                session.add_command(line)
            else:
                code_lines.append(line)

        # Join non-comment lines
        code_to_send = "\n".join(code_lines).strip()

        if not code_to_send:
            # All lines were comments
            return

        # Display the code being sent
        session.add_command(code_to_send)
        session.log_command(command)

        if self._connection:
            await self._connection.send_command(command)

    async def _handle_builtin_command(self, command: str) -> None:
        """Handle built-in slash commands."""
        session = self._get_active_session()
        if not session:
            return

        cmd = command.lower().split()[0]

        if cmd == "/help":
            session.add_info("Available commands:")
            session.add_info("  /copy    - Copy last response to clipboard")
            session.add_info("  /copyall - Copy all terminal output to clipboard")
            session.add_info("  /clear   - Clear the screen")
            session.add_info("  /quit    - Exit the terminal")
            session.add_info("  /help    - Show this help")
            session.add_info("")
            session.add_info("Keyboard shortcuts:")
            session.add_info("  Enter         - Execute (auto-continues if syntax incomplete)")
            session.add_info("  Ctrl+Enter    - Force new line (max 5 lines)")
            session.add_info("  Ctrl+J        - Force new line (alternative)")
            session.add_info("  Up/Down       - Navigate history / move cursor")
            session.add_info("  Ctrl+C        - Copy selection / Cancel / Copy last response")
            session.add_info("  Ctrl+Shift+C  - Copy last response")
            session.add_info("  Ctrl+D        - Exit terminal")
            session.add_info("  Ctrl+L        - Clear screen")
            session.add_info("  PageUp/Down   - Scroll output")
            session.add_info("")
            session.add_info("Tab shortcuts:")
            session.add_info("  Ctrl+T        - New tab")
            session.add_info("  Ctrl+W        - Close tab")
            session.add_info("  Ctrl+Tab      - Next tab")
            session.add_info("  Ctrl+Shift+Tab- Previous tab")
            session.add_info("")
            session.add_info("Comments: Lines starting with // or # are echoed but not sent")

        elif cmd == "/copy":
            self.action_copy_last_response()

        elif cmd == "/copyall":
            self._copy_all_output()

        elif cmd == "/clear":
            session.clear()

        elif cmd == "/quit":
            self.exit()

        else:
            session.add_error(f"Unknown command: {cmd}")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_clear_screen(self) -> None:
        """Clear the terminal output."""
        session = self._get_active_session()
        if session:
            session.clear()

    def action_scroll_up(self) -> None:
        """Scroll output up."""
        session = self._get_active_session()
        if session:
            scroll = session.terminal.query_one("#output-scroll")
            scroll.scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        """Scroll output down."""
        session = self._get_active_session()
        if session:
            scroll = session.terminal.query_one("#output-scroll")
            scroll.scroll_down(animate=False)

    def action_cancel_input(self) -> None:
        """Cancel current input or copy selected text (Ctrl+C behavior)."""
        command_input = self.query_one(CommandInput)
        session = self._get_active_session()

        if not session:
            return

        # Check if there's selected text in the input - copy it
        try:
            selected = command_input.selected_text
            if selected:
                pyperclip.copy(selected)
                session.add_info("Copied to clipboard")
                return
        except Exception:
            pass

        # No selection - do cancel behavior
        if command_input.value:
            # Show cancelled input and clear
            session.add_command(command_input.value + "^C")
            command_input.clear_input()
        else:
            # No input and no selection - copy last response
            if session.last_response:
                try:
                    pyperclip.copy(session.last_response)
                    session.add_info("Copied last response to clipboard")
                except Exception as e:
                    session.add_error(f"Failed to copy: {e}")
            else:
                session.add_info("^C")

    def action_copy_last_response(self) -> None:
        """Copy the last response to clipboard."""
        session = self._get_active_session()
        if not session:
            return

        if session.last_response:
            try:
                pyperclip.copy(session.last_response)
                session.add_info("Copied last response to clipboard")
            except Exception as e:
                session.add_error(f"Failed to copy: {e}")
        else:
            session.add_info("No response to copy")

    def _copy_all_output(self) -> None:
        """Copy all terminal output to clipboard."""
        session = self._get_active_session()
        if not session:
            return

        try:
            output_area = session.terminal.query_one(TextArea)
            all_text = output_area.text
            if all_text:
                pyperclip.copy(all_text)
                session.add_info("Copied all output to clipboard")
            else:
                session.add_info("No output to copy")
        except Exception as e:
            session.add_error(f"Failed to copy: {e}")

    async def action_new_tab(self) -> None:
        """Create a new tab."""
        tabs = self.query_one(TabbedContent)

        self._tab_counter += 1
        tab_id = f"session-{self._tab_counter}"
        tab_name = f"Session {self._tab_counter}"

        # Create new tab pane with session
        new_pane = TabPane(tab_name, id=tab_id)
        new_session = TerminalSession(
            session_id=tab_id,
            session_dir=self._session_dir,
            tab_suffix=f"_tab{self._tab_counter}",
            id=f"terminal-{tab_id}",
        )

        # Mount the pane and session
        await tabs.add_pane(new_pane)
        await new_pane.mount(new_session)

        # Switch to new tab
        tabs.active = tab_id

        # Focus input
        self.query_one(CommandInput).focus()

        # Show welcome in new tab
        session = self._get_active_session()
        if session:
            session.add_info(f"New session created: {tab_name}")
            session.add_info("Type /help for available commands")

    def action_close_tab(self) -> None:
        """Close the current tab."""
        tabs = self.query_one(TabbedContent)

        # Don't close if only one tab
        if tabs.tab_count <= 1:
            session = self._get_active_session()
            if session:
                session.add_info("Cannot close last tab")
            return

        # Get current tab ID and remove it
        current_tab_id = tabs.active
        if current_tab_id:
            tabs.remove_pane(current_tab_id)

        # Focus input
        self.query_one(CommandInput).focus()

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs = self.query_one(TabbedContent)
        # Get list of tab IDs
        tab_ids = [tab.id for tab in tabs.query("TabPane")]
        if not tab_ids or tabs.active not in tab_ids:
            return

        current_idx = tab_ids.index(tabs.active)
        next_idx = (current_idx + 1) % len(tab_ids)
        tabs.active = tab_ids[next_idx]

        # Focus input
        self.query_one(CommandInput).focus()

    def action_prev_tab(self) -> None:
        """Switch to the previous tab."""
        tabs = self.query_one(TabbedContent)
        # Get list of tab IDs
        tab_ids = [tab.id for tab in tabs.query("TabPane")]
        if not tab_ids or tabs.active not in tab_ids:
            return

        current_idx = tab_ids.index(tabs.active)
        prev_idx = (current_idx - 1) % len(tab_ids)
        tabs.active = tab_ids[prev_idx]

        # Focus input
        self.query_one(CommandInput).focus()
