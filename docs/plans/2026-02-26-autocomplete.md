# Autocomplete from Source Maps — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Tab-completion to the terminal by extracting API type data from Civ7's shipped `.js.map` source maps.

**Architecture:** A CLI extraction tool (`python -m civ7_terminal.extract_types`) reads all `.js.map` files from the Civ7 game directory, pulls out the embedded TypeScript source from `sourcesContent`, regex-parses method/property/type signatures for known globals (`GameplayMap`, `Players`, `Game`, etc.), and writes a structured `completions.json`. The terminal loads this JSON at startup and provides Tab-completion inside the existing `CommandInput` (TextArea subclass). A `--game-dir` CLI arg on the terminal lets users point at their install.

**Tech Stack:** Python 3.10+, `json` (stdlib), `re` (stdlib), `pathlib` (stdlib), Textual `TextArea`. No new dependencies.

---

## Task 1: Type Extraction Script — Source Map Reader

**Files:**
- Create: `civ7_terminal/extract_types.py`
- Test: manual — run against real game files

**Step 1: Create the source map reader**

The core function reads all `.js.map` files from the game directory and extracts the TypeScript source from the `sourcesContent` field.

```python
"""Extract API type information from Civ7 source maps for autocomplete."""

import argparse
import json
import re
import sys
from pathlib import Path


def find_source_maps(game_dir: Path) -> list[Path]:
    """Find all .js.map files in the game directory."""
    return sorted(game_dir.rglob("*.js.map"))


def extract_typescript_sources(map_file: Path) -> list[str]:
    """Extract TypeScript source strings from a .js.map file."""
    try:
        data = json.loads(map_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    sources_content = data.get("sourcesContent", [])
    # Filter to actual TypeScript content (skip empty/CSS/SCSS)
    return [s for s in sources_content if s and len(s) > 50 and "import" in s]
```

**Step 2: Run and verify it finds source maps**

Run: `python -c "from civ7_terminal.extract_types import find_source_maps; from pathlib import Path; maps = find_source_maps(Path(r'C:/Program Files (x86)/Steam/steamapps/common/Sid Meier''s Civilization VII')); print(f'Found {len(maps)} .js.map files')"`

Expected: `Found 609 .js.map files` (approximately)

**Step 3: Commit**

```bash
git add civ7_terminal/extract_types.py
git commit -m "feat: add source map reader for type extraction"
```

---

## Task 2: Type Extraction Script — API Parser

**Files:**
- Modify: `civ7_terminal/extract_types.py`

**Step 1: Add regex-based method extraction for known globals**

Parse all TypeScript sources for method calls on known globals. Extract method names, parameter names/types, and return types where annotated.

```python
# Known global objects to extract completions for
GLOBALS = [
    "GameplayMap", "Players", "Game", "GameContext", "Configuration",
    "UI", "WorldBuilder", "WorldUI", "Locale", "MapConstructibles",
    "MapCities", "MapUnits", "Districts", "Database", "Loading",
    "Controls", "GameInfo", "engine",
]

# Patterns to match method calls with type annotations
# e.g., GameplayMap.getOwner(x, y) or const foo: Type = GameplayMap.getOwner(...)
METHOD_CALL_RE = re.compile(
    r"(?:(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+)\s*=\s*)?"
    r"(\w+)\.([\w.]+)\s*\(",
)

# Property access without call (no parens)
PROPERTY_RE = re.compile(
    r"(?:(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+)\s*=\s*)?"
    r"(\w+)\.([\w]+)(?!\s*[(\w.])",
)


def parse_api_surface(ts_sources: list[str]) -> dict:
    """Parse TypeScript sources to extract API methods and properties.

    Returns dict like:
    {
        "GameplayMap": {
            "methods": {
                "getGridWidth": {"params": [], "return_type": "number", "count": 5},
                "getOwner": {"params": ["x", "y"], "return_type": "PlayerId", "count": 12},
            },
            "properties": {
                ...
            }
        }
    }
    """
    api = {}

    for source in ts_sources:
        # Find method calls: GlobalObj.methodName(...)
        for match in METHOD_CALL_RE.finditer(source):
            return_type = match.group(1)
            obj_name = match.group(2)
            method_chain = match.group(3)

            if obj_name not in GLOBALS:
                continue

            if obj_name not in api:
                api[obj_name] = {"methods": {}, "properties": {}}

            method_name = method_chain.split(".")[0]

            if method_name not in api[obj_name]["methods"]:
                api[obj_name]["methods"][method_name] = {
                    "params": [],
                    "return_type": None,
                    "count": 0,
                }

            entry = api[obj_name]["methods"][method_name]
            entry["count"] += 1

            if return_type and not entry["return_type"]:
                entry["return_type"] = return_type.strip()

        # Find property accesses: GlobalObj.propName (no parens after)
        for match in PROPERTY_RE.finditer(source):
            return_type = match.group(1)
            obj_name = match.group(2)
            prop_name = match.group(3)

            if obj_name not in GLOBALS:
                continue

            if obj_name not in api:
                api[obj_name] = {"methods": {}, "properties": {}}

            # Skip if already known as a method
            if prop_name in api[obj_name]["methods"]:
                continue

            if prop_name not in api[obj_name]["properties"]:
                api[obj_name]["properties"][prop_name] = {
                    "type": None,
                    "count": 0,
                }

            entry = api[obj_name]["properties"][prop_name]
            entry["count"] += 1

            if return_type and not entry["type"]:
                entry["type"] = return_type.strip()

    return api
```

**Step 2: Add parameter extraction**

Extract parameter names from function call sites using a more targeted regex:

```python
PARAM_EXTRACT_RE = re.compile(
    r"(\w+)\.([\w]+)\s*\(([^)]*)\)",
)


def extract_params(ts_sources: list[str], api: dict) -> None:
    """Extract parameter names for known methods from call sites."""
    for source in ts_sources:
        for match in PARAM_EXTRACT_RE.finditer(source):
            obj_name = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3).strip()

            if obj_name not in api:
                continue
            if method_name not in api[obj_name]["methods"]:
                continue

            entry = api[obj_name]["methods"][method_name]

            # Only update if we don't have params yet and this looks like
            # a definition (has type annotations with colons)
            if not entry["params"] and ":" in params_str:
                params = []
                for p in params_str.split(","):
                    p = p.strip()
                    if ":" in p:
                        name = p.split(":")[0].strip()
                        params.append(name)
                    elif p:
                        params.append(p)
                if params:
                    entry["params"] = params
```

**Step 3: Commit**

```bash
git add civ7_terminal/extract_types.py
git commit -m "feat: add API parser for source map TypeScript"
```

---

## Task 3: Type Extraction Script — Sub-Object Parsing

**Files:**
- Modify: `civ7_terminal/extract_types.py`

**Step 1: Extract sub-object members (player.Cities, player.Diplomacy, etc.)**

The tricky part: `Players.get(id)` returns a player instance, which has sub-objects like `.Cities`, `.Diplomacy`, `.Treasury`. We need to follow the chain.

```python
# Sub-object access patterns
# e.g., player.Cities.getCities(), p.Diplomacy.hasMet(otherId)
SUB_OBJECT_RE = re.compile(
    r"(?:(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+)\s*=\s*)?"
    r"\w+\.(Cities|Units|Techs|Culture|Treasury|Diplomacy|Resources|Trade|"
    r"Districts|Religion|Happiness|Visibility|AI|Armies|Formations|"
    r"Constructibles|GreatPeoplePoints|Espionage|Influence|Modifiers|"
    r"Growth|Production|Yields|BuildQueue|Combat|Health|Movement|Experience|"
    r"Workers|Scoring|Stats|TurnManager|Identity|Victories|Ages|"
    r"VictoryManager|CityStates|RandomEvents|CrisisManager|EconomicRules|"
    r"Unlocks|ProgressionTrees|PlacementRules|Summary|AgeProgressManager|"
    r"IndependentPowers|Notifications|DiplomacyDeals|DiplomacySessions|"
    r"CityCommands|CityOperations|UnitCommands|UnitOperations|PlayerOperations"
    r")\.([\w]+)\s*(\()?",
)


def parse_sub_objects(ts_sources: list[str]) -> dict:
    """Parse sub-object methods/properties (e.g., player.Cities.getCities()).

    Returns dict like:
    {
        "Cities": {
            "methods": {"getCities": {...}, "getCapital": {...}},
            "properties": {...}
        }
    }
    """
    subs = {}

    for source in ts_sources:
        for match in SUB_OBJECT_RE.finditer(source):
            return_type = match.group(1)
            sub_name = match.group(2)
            member_name = match.group(3)
            has_parens = match.group(4)

            if sub_name not in subs:
                subs[sub_name] = {"methods": {}, "properties": {}}

            if has_parens:
                if member_name not in subs[sub_name]["methods"]:
                    subs[sub_name]["methods"][member_name] = {
                        "params": [],
                        "return_type": return_type.strip() if return_type else None,
                        "count": 0,
                    }
                subs[sub_name]["methods"][member_name]["count"] += 1
            else:
                if member_name not in subs[sub_name]["methods"]:
                    if member_name not in subs[sub_name]["properties"]:
                        subs[sub_name]["properties"][member_name] = {
                            "type": return_type.strip() if return_type else None,
                            "count": 0,
                        }
                    subs[sub_name]["properties"][member_name]["count"] += 1

    return subs
```

**Step 2: Commit**

```bash
git add civ7_terminal/extract_types.py
git commit -m "feat: add sub-object member parsing"
```

---

## Task 4: Type Extraction Script — CLI and JSON Output

**Files:**
- Modify: `civ7_terminal/extract_types.py`

**Step 1: Add the main CLI and JSON writer**

```python
def build_completions(game_dir: Path) -> dict:
    """Build the full completions dictionary from game source maps."""
    print(f"Scanning {game_dir} for source maps...")
    map_files = find_source_maps(game_dir)
    print(f"Found {len(map_files)} .js.map files")

    print("Extracting TypeScript sources...")
    all_sources = []
    for mf in map_files:
        all_sources.extend(extract_typescript_sources(mf))
    print(f"Extracted {len(all_sources)} TypeScript sources")

    print("Parsing API surface...")
    api = parse_api_surface(all_sources)
    extract_params(all_sources, api)

    print("Parsing sub-object members...")
    subs = parse_sub_objects(all_sources)

    # Build final completions structure
    completions = {
        "version": 1,
        "globals": {},
        "sub_objects": {},
    }

    for obj_name, data in sorted(api.items()):
        completions["globals"][obj_name] = {
            "methods": {
                name: {
                    "params": info["params"],
                    "return_type": info["return_type"],
                }
                for name, info in sorted(data["methods"].items())
            },
            "properties": {
                name: {"type": info["type"]}
                for name, info in sorted(data["properties"].items())
            },
        }

    for sub_name, data in sorted(subs.items()):
        completions["sub_objects"][sub_name] = {
            "methods": {
                name: {
                    "params": info["params"],
                    "return_type": info["return_type"],
                }
                for name, info in sorted(data["methods"].items())
            },
            "properties": {
                name: {"type": info["type"]}
                for name, info in sorted(data["properties"].items())
            },
        }

    return completions


# Common Steam install paths by platform
STEAM_PATHS = [
    # Windows
    Path("C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VII"),
    Path("C:/Program Files/Steam/steamapps/common/Sid Meier's Civilization VII"),
    Path("D:/Steam/steamapps/common/Sid Meier's Civilization VII"),
    Path("D:/SteamLibrary/steamapps/common/Sid Meier's Civilization VII"),
    # Linux
    Path.home() / ".steam/steam/steamapps/common/Sid Meier's Civilization VII",
    Path.home() / ".local/share/Steam/steamapps/common/Sid Meier's Civilization VII",
    # macOS
    Path.home() / "Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII",
]


def find_game_dir() -> Path | None:
    """Try to auto-detect the Civ7 game directory."""
    for p in STEAM_PATHS:
        if p.is_dir():
            return p
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="civ7-extract-types",
        description="Extract Civ7 API types from game source maps for autocomplete",
    )
    parser.add_argument(
        "--game-dir", "-g",
        type=Path,
        default=None,
        help="Path to Civ7 game directory (auto-detected if not provided)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output JSON file (default: completions.json next to this script)",
    )
    args = parser.parse_args()

    game_dir = args.game_dir or find_game_dir()
    if not game_dir:
        print("ERROR: Could not find Civ7 game directory.", file=sys.stderr)
        print("Provide --game-dir /path/to/Sid Meier's Civilization VII", file=sys.stderr)
        sys.exit(1)

    if not game_dir.is_dir():
        print(f"ERROR: {game_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    output = args.output or Path(__file__).resolve().parent.parent / "completions.json"

    completions = build_completions(game_dir)

    # Stats
    total_methods = sum(
        len(g["methods"])
        for g in completions["globals"].values()
    )
    total_props = sum(
        len(g["properties"])
        for g in completions["globals"].values()
    )
    total_sub_methods = sum(
        len(s["methods"])
        for s in completions["sub_objects"].values()
    )
    total_sub_props = sum(
        len(s["properties"])
        for s in completions["sub_objects"].values()
    )

    output.write_text(json.dumps(completions, indent=2), encoding="utf-8")

    print(f"\nDone! Wrote {output}")
    print(f"  Globals: {len(completions['globals'])} objects, "
          f"{total_methods} methods, {total_props} properties")
    print(f"  Sub-objects: {len(completions['sub_objects'])} objects, "
          f"{total_sub_methods} methods, {total_sub_props} properties")


if __name__ == "__main__":
    main()
```

**Step 2: Add script entry point to pyproject.toml**

In `pyproject.toml`, under `[project.scripts]`, add:
```
civ7-extract-types = "civ7_terminal.extract_types:main"
```

**Step 3: Run the extraction against the real game**

Run: `python -m civ7_terminal.extract_types`

Expected: Auto-detects game path, processes ~609 maps, writes `completions.json` with stats showing hundreds of methods/properties.

**Step 4: Inspect the output**

Run: `python -c "import json; d=json.load(open('completions.json')); print(json.dumps({k: len(v['methods']) for k,v in d['globals'].items()}, indent=2))"`

Expected: JSON showing method counts per global object.

**Step 5: Commit**

```bash
git add civ7_terminal/extract_types.py pyproject.toml
git commit -m "feat: add CLI for type extraction with JSON output"
```

---

## Task 5: Completions Engine

**Files:**
- Create: `civ7_terminal/completions.py`

**Step 1: Create the completions engine that loads JSON and provides matches**

```python
"""Autocomplete engine for Civ7 JavaScript API."""

import json
from pathlib import Path


class CompletionEngine:
    """Provides Tab-completions from a completions.json file."""

    def __init__(self):
        self._globals: dict = {}       # {"GameplayMap": {"methods": {...}, "properties": {...}}}
        self._sub_objects: dict = {}   # {"Cities": {"methods": {...}, "properties": {...}}}
        self._global_names: list[str] = []  # ["GameplayMap", "Players", "Game", ...]
        self._loaded = False

    def load(self, path: Path) -> bool:
        """Load completions from a JSON file. Returns True if successful."""
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._globals = data.get("globals", {})
            self._sub_objects = data.get("sub_objects", {})
            self._global_names = sorted(self._globals.keys())
            self._loaded = True
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_completions(self, text: str, cursor_pos: int) -> list[str]:
        """Get completions for the token at cursor position.

        Args:
            text: Full input text
            cursor_pos: Character position of cursor

        Returns:
            List of completion strings (just the completing part, not the full token).
        """
        if not self._loaded:
            return []

        # Extract the token before the cursor
        token = self._extract_token(text, cursor_pos)
        if not token:
            return []

        # Case 1: "GameplayM" -> complete global names
        if "." not in token:
            return [
                name for name in self._global_names
                if name.startswith(token) and name != token
            ]

        parts = token.rsplit(".", 1)
        obj_path = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        # Case 2: "GameplayMap.getGr" -> complete methods/properties on a global
        if obj_path in self._globals:
            return self._match_members(self._globals[obj_path], prefix)

        # Case 3: "Game.Diplomacy.ha" -> complete on Game sub-system
        if "." in obj_path:
            # e.g., obj_path = "Game.Diplomacy", try "Diplomacy" as sub_object
            sub_name = obj_path.rsplit(".", 1)[1]
            if sub_name in self._sub_objects:
                return self._match_members(self._sub_objects[sub_name], prefix)

        # Case 4: any sub-object reference like "player.Cities.get"
        # Try to match the last segment before the final dot
        last_segment = obj_path.rsplit(".", 1)[-1]
        if last_segment in self._sub_objects:
            return self._match_members(self._sub_objects[last_segment], prefix)

        return []

    def get_signature(self, text: str, cursor_pos: int) -> str | None:
        """Get the method signature for the token at cursor, if it's a known method.

        Returns a string like "getOwner(x, y) -> PlayerId" or None.
        """
        if not self._loaded:
            return None

        token = self._extract_token(text, cursor_pos)
        if not token or "." not in token:
            return None

        parts = token.rsplit(".", 1)
        obj_path = parts[0]
        member = parts[1] if len(parts) > 1 else ""

        # Look up in globals
        if obj_path in self._globals:
            return self._format_signature(self._globals[obj_path], member)

        # Look up in sub-objects
        last_segment = obj_path.rsplit(".", 1)[-1]
        if last_segment in self._sub_objects:
            return self._format_signature(self._sub_objects[last_segment], member)

        return None

    def _extract_token(self, text: str, cursor_pos: int) -> str:
        """Extract the dotted token immediately before the cursor."""
        # Work backwards from cursor to find the start of the token
        left = text[:cursor_pos]
        # Token chars: alphanumeric, underscore, dot
        token_chars = []
        for ch in reversed(left):
            if ch.isalnum() or ch in ("_", "."):
                token_chars.append(ch)
            else:
                break
        return "".join(reversed(token_chars))

    def _match_members(self, obj_data: dict, prefix: str) -> list[str]:
        """Return matching method and property names."""
        results = []
        for name in sorted(obj_data.get("methods", {})):
            if name.startswith(prefix) and name != prefix:
                # Append () to indicate it's a method
                results.append(name)
        for name in sorted(obj_data.get("properties", {})):
            if name.startswith(prefix) and name != prefix:
                results.append(name)
        return results

    def _format_signature(self, obj_data: dict, member: str) -> str | None:
        """Format a signature string for a method."""
        methods = obj_data.get("methods", {})
        if member in methods:
            info = methods[member]
            params = ", ".join(info.get("params", []))
            ret = info.get("return_type")
            sig = f"{member}({params})"
            if ret:
                sig += f" -> {ret}"
            return sig

        props = obj_data.get("properties", {})
        if member in props:
            ptype = props[member].get("type")
            if ptype:
                return f"{member}: {ptype}"
            return f"{member}"

        return None
```

**Step 2: Commit**

```bash
git add civ7_terminal/completions.py
git commit -m "feat: add completions engine with dotted-path lookup"
```

---

## Task 6: Tab Completion in CommandInput

**Files:**
- Modify: `civ7_terminal/app.py` (CommandInput class)

**Step 1: Add Tab binding and completion state to CommandInput**

Add to `CommandInput.BINDINGS`:
```python
Binding("tab", "complete", "Complete", show=False, priority=True),
```

Add to `CommandInput.__init__`:
```python
self._completions: list[str] = []
self._completion_index: int = -1
self._completion_prefix: str = ""  # The token being completed
self._completion_engine: CompletionEngine | None = None
```

Add method:
```python
def set_completion_engine(self, engine):
    """Set the completion engine."""
    self._completion_engine = engine
```

**Step 2: Implement action_complete**

```python
def action_complete(self) -> None:
    """Tab completion for API methods/properties."""
    if not self._completion_engine or not self._completion_engine.is_loaded:
        return

    # Get cursor position as a character offset
    row, col = self.cursor_location
    lines = self.text.split("\n")
    cursor_pos = sum(len(lines[i]) + 1 for i in range(row)) + col

    if self._completions and self._completion_prefix:
        # Cycle through existing completions
        self._completion_index = (self._completion_index + 1) % len(self._completions)
        self._apply_completion()
    else:
        # Start new completion
        matches = self._completion_engine.get_completions(self.text, cursor_pos)
        if not matches:
            return

        if len(matches) == 1:
            # Single match — apply immediately
            self._completions = matches
            self._completion_index = 0
            self._completion_prefix = self._get_current_partial()
            self._apply_completion()
        else:
            # Multiple matches — start cycling
            self._completions = matches
            self._completion_index = 0
            self._completion_prefix = self._get_current_partial()
            self._apply_completion()

def _get_current_partial(self) -> str:
    """Get the partial token being typed (after the last dot)."""
    row, col = self.cursor_location
    line = self.text.split("\n")[row]
    left = line[:col]
    # Walk backwards to find the last dot or non-token char
    partial = []
    for ch in reversed(left):
        if ch == ".":
            break
        elif ch.isalnum() or ch == "_":
            partial.append(ch)
        else:
            break
    return "".join(reversed(partial))

def _apply_completion(self) -> None:
    """Replace the current partial with the selected completion."""
    if not self._completions:
        return

    completion = self._completions[self._completion_index]
    partial = self._completion_prefix

    # Delete the partial text and insert the completion
    row, col = self.cursor_location
    start_col = col - len(partial)

    # Select the partial text and replace it
    self.selection = ((row, start_col), (row, col))
    self.replace(completion, *self.selection)

    # Move cursor to end of inserted text
    new_col = start_col + len(completion)
    self.move_cursor((row, new_col))
```

**Step 3: Reset completions on any non-Tab key**

Override `on_key` in CommandInput to reset completion state when the user types anything other than Tab:

```python
def on_key(self, event: Key) -> None:
    """Reset completion state on non-Tab keypress."""
    if event.key != "tab":
        self._completions = []
        self._completion_index = -1
        self._completion_prefix = ""
```

**Step 4: Commit**

```bash
git add civ7_terminal/app.py
git commit -m "feat: add Tab completion to CommandInput"
```

---

## Task 7: Wire Up — Load Completions at App Startup

**Files:**
- Modify: `civ7_terminal/app.py` (Civ7TerminalApp class)
- Modify: `civ7_terminal/__main__.py`

**Step 1: Add --game-dir CLI argument to __main__.py**

In `parse_args()`, add:
```python
parser.add_argument(
    "--game-dir",
    "-g",
    type=str,
    default=None,
    help="Civ7 game directory (for autocomplete). Run 'python -m civ7_terminal.extract_types' first.",
)
```

Pass to app:
```python
app = Civ7TerminalApp(
    host=args.host,
    port=args.port,
    session_dir=args.session_dir,
    game_dir=args.game_dir,
)
```

**Step 2: Load completions.json in Civ7TerminalApp.on_mount**

In `Civ7TerminalApp.__init__`, accept `game_dir` parameter and store it.

In `on_mount`, after setting up the connection:

```python
from .completions import CompletionEngine

# Load autocomplete data
completions_path = Path(__file__).resolve().parent.parent / "completions.json"
engine = CompletionEngine()
if engine.load(completions_path):
    command_input = self.query_one(CommandInput)
    command_input.set_completion_engine(engine)
    # Show in first tab
    session = self._get_active_session()
    if session:
        session.add_info("Autocomplete loaded — press Tab to complete")
```

**Step 3: Commit**

```bash
git add civ7_terminal/app.py civ7_terminal/__main__.py
git commit -m "feat: wire up completions engine to terminal startup"
```

---

## Task 8: Run Extraction and End-to-End Test

**Step 1: Run the extraction tool**

Run: `python -m civ7_terminal.extract_types`

Verify: `completions.json` is created with real data.

**Step 2: Launch the terminal and test Tab completion**

Run: `python -m civ7_terminal`

Test these scenarios:
1. Type `Game` + Tab → cycles through `GameplayMap`, `GameContext`, `GameInfo`, etc.
2. Type `GameplayMap.` + Tab → shows first method
3. Type `GameplayMap.get` + Tab → cycles through `getGridWidth`, `getGridHeight`, etc.
4. Type `Players.get` + Tab → completes to `getAliveMajorIds` or similar
5. Type any non-matching text + Tab → nothing happens
6. Tab cycling resets when you type a character

**Step 3: Add completions.json to .gitignore**

Since it's machine-specific (depends on game install path), add to `.gitignore`:
```
completions.json
```

**Step 4: Commit**

```bash
git add .gitignore
git commit -m "feat: add completions.json to gitignore, extraction verified"
```

---

## Task 9: Update Docs

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Step 1: Add Autocomplete section to README**

After the "Keybindings" section, add:

```markdown
## Autocomplete

Tab completion for the Civ7 JavaScript API. Extracts type data directly from the game's source maps.

### Setup

```bash
# Extract types from your game install (auto-detects Steam path)
python -m civ7_terminal.extract_types

# Or specify the path manually
python -m civ7_terminal.extract_types --game-dir "/path/to/Sid Meier's Civilization VII"
```

This creates a `completions.json` file. Re-run after game updates.

### Usage

- Type a global name and press **Tab** to complete: `GameplayM` → `GameplayMap`
- After a dot, Tab completes methods/properties: `GameplayMap.getGr` → `GameplayMap.getGridWidth`
- Press Tab repeatedly to cycle through matches
- Works with sub-objects too: `player.Cities.get` → `player.Cities.getCities`
```

**Step 2: Update CLAUDE.md project structure**

Add `extract_types.py` and `completions.py` to the structure listing.

**Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add autocomplete setup instructions"
```

---

## Task 10: Triple Verification

**Step 1: Verify extraction produces valid data**

```bash
python -m civ7_terminal.extract_types
python -c "
import json
d = json.load(open('completions.json'))
assert d['version'] == 1
assert 'GameplayMap' in d['globals']
assert len(d['globals']['GameplayMap']['methods']) > 30
assert 'Players' in d['globals']
print('PASS: Extraction data valid')
print(f'  {len(d[\"globals\"])} globals, {len(d[\"sub_objects\"])} sub-objects')
for name, obj in sorted(d['globals'].items()):
    print(f'  {name}: {len(obj[\"methods\"])} methods, {len(obj[\"properties\"])} props')
"
```

**Step 2: Verify completions engine returns correct results**

```bash
python -c "
from pathlib import Path
from civ7_terminal.completions import CompletionEngine
e = CompletionEngine()
assert e.load(Path('completions.json'))

# Test global name completion
r = e.get_completions('GameplayM', 9)
assert 'GameplayMap' in r, f'Expected GameplayMap, got {r}'

# Test method completion
r = e.get_completions('GameplayMap.getGrid', 19)
assert any('getGridWidth' in x for x in r), f'Expected getGridWidth, got {r}'

# Test sub-object completion
r = e.get_completions('player.Cities.get', 17)
assert any('getCities' in x for x in r), f'Expected getCities, got {r}'

# Test empty/no match
r = e.get_completions('zzzzNothing.', 12)
assert r == [], f'Expected empty, got {r}'

print('PASS: All completion engine tests pass')
"
```

**Step 3: Verify terminal launches with completions loaded**

```bash
python -c "
from civ7_terminal.app import Civ7TerminalApp, CommandInput
from civ7_terminal.completions import CompletionEngine
from pathlib import Path

e = CompletionEngine()
loaded = e.load(Path('completions.json'))
assert loaded, 'Failed to load completions.json'

ci = CommandInput(id='test')
ci.set_completion_engine(e)
assert ci._completion_engine is not None
assert ci._completion_engine.is_loaded

print('PASS: Terminal integration verified')
"
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: autocomplete from source maps — complete"
```
