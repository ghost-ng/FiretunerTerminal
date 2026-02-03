"""Terminal output widget for displaying command history and responses."""

import json
from typing import Optional

from rich.segment import Segment
from rich.style import Style
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import TextArea

# Single-char control codes as line color markers (invisible, easy to strip)
MARK_CYAN = "\x01"      # SOH - Commands
MARK_GREEN = "\x02"     # STX - Responses
MARK_RED = "\x03"       # ETX - Errors
MARK_YELLOW = "\x04"    # EOT - Info

# Map markers to Rich styles
MARKER_STYLES = {
    "\x01": Style(color="#00ffff"),        # Cyan - commands
    "\x02": Style(color="green"),          # Green - responses
    "\x03": Style(color="red", bold=True), # Red - errors
    "\x04": Style(color="yellow"),         # Yellow - info
}


class HighlightedTextArea(TextArea):
    """TextArea with marker-based color highlighting."""

    def render_line(self, y: int) -> Strip:
        """Render a line, using first-char marker for color."""
        strip = super().render_line(y)

        # y is visual row - add scroll offset to get document line
        doc_line = y + self.scroll_offset.y
        if doc_line < self.document.line_count:
            line = self.document.get_line(doc_line)

            # Check for color marker at start of line
            if line and line[0] in MARKER_STYLES:
                marker = line[0]
                color_style = MARKER_STYLES[marker]

                # Rebuild strip: strip marker char, apply color
                new_segments = []
                stripped_marker = False

                for seg in strip:
                    if seg.control:
                        new_segments.append(seg)
                        continue

                    text = seg.text

                    # Strip the marker from first text segment
                    if not stripped_marker and text:
                        if text[0] == marker:
                            text = text[1:]
                            stripped_marker = True

                    if not text:
                        continue

                    # Apply our color, preserve selection bgcolor
                    if seg.style and seg.style.bgcolor:
                        new_style = Style(
                            color=color_style.color,
                            bgcolor=seg.style.bgcolor,
                            bold=color_style.bold,
                        )
                    else:
                        new_style = color_style

                    new_segments.append(Segment(text, new_style, seg.control))

                return Strip(new_segments)

        return strip


class TerminalOutput(Widget):
    """
    Scrollable terminal output display with selectable, colored text.

    Shows command history and responses with distinct colors:
    - Commands: cyan
    - Responses: green
    - Errors: red
    - Info: yellow
    """

    DEFAULT_CSS = """
    TerminalOutput {
        width: 100%;
        height: 1fr;
    }

    TerminalOutput > TextArea {
        width: 100%;
        height: 100%;
        border: solid $primary;
        background: $surface;
    }

    TerminalOutput > TextArea:focus {
        border: solid $primary;
    }
    """

    raw_mode: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        """Compose the terminal output layout."""
        yield HighlightedTextArea(id="output-scroll", read_only=True)

    def on_mount(self) -> None:
        """Configure the text area on mount."""
        text_area = self.query_one(TextArea)
        text_area.show_line_numbers = False

    def add_command(self, command: str) -> None:
        """
        Add a command to the output.

        Args:
            command: The command string entered by the user.
        """
        # Handle multiline commands - each line gets cyan marker
        lines = command.split("\n")
        for i, line in enumerate(lines):
            if i == 0:
                self._append_line(f"{MARK_CYAN}> {line}")
            else:
                self._append_line(f"{MARK_CYAN}{line}")

        self._scroll_to_bottom()

    def add_response(self, response: str) -> None:
        """
        Add a response to the output.

        Args:
            response: The response string from the server.
        """
        if self.raw_mode:
            formatted = response
        else:
            formatted = self._format_response(response)

        # Add green marker to each line
        lines = formatted.split("\n")
        for line in lines:
            self._append_line(f"{MARK_GREEN}{line}")

        self._scroll_to_bottom()

    def add_error(self, error: str) -> None:
        """
        Add an error message to the output.

        Args:
            error: The error message.
        """
        self._append_line(f"{MARK_RED}ERROR: {error}")
        self._scroll_to_bottom()

    def add_info(self, info: str) -> None:
        """
        Add an info message to the output.

        Args:
            info: The info message.
        """
        self._append_line(f"{MARK_YELLOW}INFO: {info}")
        self._scroll_to_bottom()

    def clear(self) -> None:
        """Clear all output."""
        text_area = self.query_one(TextArea)
        text_area.load_text("")

    def toggle_raw_mode(self) -> bool:
        """
        Toggle raw output mode.

        Returns:
            The new raw mode state.
        """
        self.raw_mode = not self.raw_mode
        return self.raw_mode

    def _append_line(self, text: str) -> None:
        """Append a line to the output."""
        text_area = self.query_one(TextArea)
        current = text_area.text
        if current:
            text_area.load_text(current + "\n" + text)
        else:
            text_area.load_text(text)

    def _format_response(self, response: str) -> str:
        """
        Format response for display.

        Attempts to pretty-print JSON.
        """
        stripped = response.strip()

        # Try to parse as JSON and pretty-print
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass

        return response

    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the output."""
        text_area = self.query_one(TextArea)
        line_count = text_area.document.line_count
        if line_count > 0:
            text_area.cursor_location = (line_count - 1, 0)
