"""Completion engine for Civ7 JavaScript API autocomplete.

Loads completions.json (produced by extract_types.py) and provides
completions and method signatures for the CommandInput widget.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class CompletionEngine:
    """Provides tab-completion candidates and method signatures."""

    def __init__(self) -> None:
        self._globals: dict[str, dict] = {}
        self._sub_objects: dict[str, dict] = {}
        self._loaded: bool = False

    def load(self, path: Path) -> bool:
        """Load completions data from a JSON file.

        Returns True if loaded successfully, False otherwise.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Failed to load completions from %s: %s", path, exc)
            return False

        self._globals = data.get("globals", {})
        self._sub_objects = data.get("sub_objects", {})
        self._loaded = True
        log.info(
            "Loaded completions: %d globals, %d sub-objects",
            len(self._globals),
            len(self._sub_objects),
        )
        return True

    @property
    def is_loaded(self) -> bool:
        """Whether completions data has been loaded."""
        return self._loaded

    # -----------------------------------------------------------------
    # Completions
    # -----------------------------------------------------------------

    def get_completions(self, text: str, cursor_pos: int) -> list[str]:
        """Return completion candidates for the token at *cursor_pos*.

        Handles:
        1. Global name completion:  ``GameplayM|`` -> ``["GameplayMap"]``
        2. Method/property on global: ``GameplayMap.getGr|`` -> ``[...]``
        3. Sub-object on Game: ``Game.Diplomacy.ha|`` -> ``[...]``
        4. Sub-object via variable: ``player.Cities.get|`` -> ``[...]``
        5. No match: ``zzz.|`` -> ``[]``
        """
        if not self._loaded:
            return []

        token = self._extract_token(text, cursor_pos)
        if not token:
            return []

        parts = token.split(".")

        if len(parts) == 1:
            # Case 1: Global name prefix
            prefix = parts[0].lower()
            return sorted(
                name
                for name in self._globals
                if name.lower().startswith(prefix)
            )

        if len(parts) == 2:
            obj_name, member_prefix = parts
            member_prefix_lower = member_prefix.lower()

            # Case 2: method/property on a known global
            if obj_name in self._globals:
                return self._match_members(self._globals[obj_name], member_prefix_lower)

            # Case 4: ``variable.SubObject`` -- the first part is a variable,
            # second part could be a sub-object name prefix OR already a
            # sub-object whose members we want.
            # First check if obj_name itself is a sub-object (unlikely at 2-part,
            # but handle ``Cities.get``).
            if obj_name in self._sub_objects:
                return self._match_members(self._sub_objects[obj_name], member_prefix_lower)

            # Otherwise the first part is an unknown variable, second part
            # could be a sub-object name prefix (``player.Cit`` -> ``Cities``).
            # Require a non-empty prefix to avoid flooding with all sub-objects
            # on a bare ``zzz.`` input.
            if not member_prefix:
                return []
            return sorted(
                name
                for name in self._sub_objects
                if name.lower().startswith(member_prefix_lower)
            )

        if len(parts) == 3:
            # Cases 3 & 4:  ``Game.Diplomacy.ha`` or ``player.Cities.get``
            obj_name, sub_name, member_prefix = parts
            member_prefix_lower = member_prefix.lower()

            # Try to resolve the sub-object
            if sub_name in self._sub_objects:
                return self._match_members(self._sub_objects[sub_name], member_prefix_lower)

            # Sub-name might also be a global (e.g. ``Game.Districts.get``)
            # ``Districts`` exists in both globals and sub_objects -- prefer sub_objects
            # since the pattern is ``something.SubObject.method``.
            return []

        # Deeper nesting -- not supported
        return []

    def get_signature(self, text: str, cursor_pos: int) -> str | None:
        """Return a signature string for the method at *cursor_pos*.

        Example return: ``"getOwner(x, y) -> PlayerId"``
        """
        if not self._loaded:
            return None

        token = self._extract_token(text, cursor_pos)
        if not token:
            return None

        parts = token.split(".")

        method_name: str | None = None
        source: dict | None = None

        if len(parts) == 2:
            obj_name, method_name = parts
            if obj_name in self._globals:
                source = self._globals[obj_name]
            elif obj_name in self._sub_objects:
                source = self._sub_objects[obj_name]

        elif len(parts) == 3:
            _, sub_name, method_name = parts
            if sub_name in self._sub_objects:
                source = self._sub_objects[sub_name]
            elif sub_name in self._globals:
                source = self._globals[sub_name]

        if source is None or method_name is None:
            return None

        method_info = source.get("methods", {}).get(method_name)
        if method_info is None:
            return None

        params_str = ", ".join(method_info.get("params", []))
        sig = f"{method_name}({params_str})"
        ret = method_info.get("return_type")
        if ret:
            sig += f" -> {ret}"
        return sig

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _extract_token(text: str, cursor_pos: int) -> str:
        """Extract the dotted identifier token ending at *cursor_pos*.

        Walks backwards from the cursor collecting alphanumeric, underscore,
        and dot characters.
        """
        # Clamp cursor_pos to text length
        cursor_pos = min(cursor_pos, len(text))

        i = cursor_pos - 1
        while i >= 0:
            ch = text[i]
            if ch.isalnum() or ch == "_" or ch == ".":
                i -= 1
            else:
                break
        return text[i + 1 : cursor_pos]

    @staticmethod
    def _match_members(obj_data: dict, prefix_lower: str) -> list[str]:
        """Return sorted method/property names matching *prefix_lower*."""
        names: list[str] = []
        for name in obj_data.get("methods", {}):
            if name.lower().startswith(prefix_lower):
                names.append(name)
        for name in obj_data.get("properties", {}):
            if name.lower().startswith(prefix_lower):
                names.append(name)
        return sorted(names)
