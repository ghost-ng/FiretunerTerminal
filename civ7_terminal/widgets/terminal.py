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


class HighlightedTextArea(TextArea):
    """TextArea with line-based color highlighting."""

    def render_line(self, y: int) -> Strip:
        """Render a line with custom colors based on prefix."""
        strip = super().render_line(y)

        # Get the actual line content to determine color
        if y < self.document.line_count:
            line = self.document.get_line(y)

            # Determine style based on line prefix
            if line.startswith("> ") or line.startswith("  "):
                color_style = Style(color="cyan")
            elif line.startswith("ERROR:"):
                color_style = Style(color="red", bold=True)
            elif line.startswith("INFO:"):
                color_style = Style(color="yellow")
            else:
                color_style = Style(color="green")

            # Rebuild strip with our color applied
            new_segments = []
            for seg in strip:
                if seg.control:
                    # Keep control segments unchanged
                    new_segments.append(seg)
                else:
                    # Apply our color, but let existing style (selection) override
                    combined = color_style + (seg.style or Style())
                    new_segments.append(Segment(seg.text, combined, seg.control))

            return Strip(new_segments, strip.cell_length)

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
        # Handle multiline commands
        lines = command.split("\n")
        for i, line in enumerate(lines):
            if i == 0:
                self._append_line(f"> {line}")
            else:
                self._append_line(f"  {line}")

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

        self._append_line(formatted)
        self._scroll_to_bottom()

    def add_error(self, error: str) -> None:
        """
        Add an error message to the output.

        Args:
            error: The error message.
        """
        self._append_line(f"ERROR: {error}")
        self._scroll_to_bottom()

    def add_info(self, info: str) -> None:
        """
        Add an info message to the output.

        Args:
            info: The info message.
        """
        self._append_line(f"INFO: {info}")
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
