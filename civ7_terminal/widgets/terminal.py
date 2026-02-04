"""Terminal output widget for displaying command history and responses."""

import json
from typing import Optional

from rich.segment import Segment
from rich.style import Style
from textual.app import ComposeResult
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import TextArea

# Color styles for different line types
STYLE_COMMAND = Style(color="#00ffff")        # Cyan
STYLE_RESPONSE = Style(color="green")         # Green
STYLE_ERROR = Style(color="red", bold=True)   # Red
STYLE_INFO = Style(color="yellow")            # Yellow


class HighlightedTextArea(TextArea):
    """TextArea with prefix-based color highlighting."""

    def render_line(self, y: int) -> Strip:
        """Render a line with color based on prefix."""
        strip = super().render_line(y)

        # y is visual row - add scroll offset to get document line
        doc_line = y + self.scroll_offset.y
        if doc_line < self.document.line_count:
            line = self.document.get_line(doc_line)

            # Determine color based on line prefix
            if line.startswith("> "):
                color_style = STYLE_COMMAND
            elif line.startswith("ERROR:"):
                color_style = STYLE_ERROR
            elif line.startswith("INFO:"):
                color_style = STYLE_INFO
            else:
                color_style = STYLE_RESPONSE

            # Rebuild strip with our color
            new_segments = []
            for seg in strip:
                if seg.control:
                    new_segments.append(seg)
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

                new_segments.append(Segment(seg.text, new_style, seg.control))

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
        # Handle multiline commands - first line gets "> " prefix
        lines = command.split("\n")
        for i, line in enumerate(lines):
            if i == 0:
                self._append_line(f"> {line}")
            else:
                self._append_line(f"> {line}")

        self._scroll_to_bottom()

    def add_response(self, response: str) -> None:
        """
        Add a response to the output.

        Args:
            response: The response string from the server.
        """
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
