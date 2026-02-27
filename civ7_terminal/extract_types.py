"""Extract TypeScript type information from Civ7 source maps for autocomplete.

Scans .js.map files in the Civ7 game directory, extracts TypeScript source from
the sourcesContent field, and regex-parses method/property/type signatures for
known global objects and sub-objects. Writes a structured completions.json file.

Usage:
    python -m civ7_terminal.extract_types [--game-dir PATH] [--output PATH]
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Known globals to extract members for
# ---------------------------------------------------------------------------
KNOWN_GLOBALS = [
    "GameplayMap",
    "Players",
    "Game",
    "GameContext",
    "Configuration",
    "UI",
    "WorldBuilder",
    "WorldUI",
    "Locale",
    "MapConstructibles",
    "MapCities",
    "MapUnits",
    "Districts",
    "Database",
    "Loading",
    "Controls",
    "GameInfo",
    "engine",
]

# ---------------------------------------------------------------------------
# Known sub-objects that appear on player instances or Game
# These are accessed like player.Cities.getCities() or Game.Diplomacy.hasMet()
# ---------------------------------------------------------------------------
KNOWN_SUB_OBJECTS = [
    "Cities",
    "Units",
    "Techs",
    "Culture",
    "Treasury",
    "Diplomacy",
    "Resources",
    "Trade",
    "Districts",
    "Religion",
    "Happiness",
    "Visibility",
    "Growth",
    "Production",
    "Yields",
    "BuildQueue",
    "Combat",
    "Health",
    "Movement",
    "Experience",
    "VictoryManager",
    "CityStates",
    "RandomEvents",
    "CrisisManager",
    "Notifications",
    "PlayerOperations",
    "UnitOperations",
    "CityOperations",
    "UnitCommands",
    "CityCommands",
    "DiplomacyDeals",
    "DiplomacySessions",
    "Armies",
    "Constructibles",
    "DiplomacyTreasury",
    "Influence",
    "LegacyPaths",
    "AdvancedStart",
    "Stats",
    "AgeProgressManager",
    "IndependentPowers",
    "PlacementRules",
    "EconomicRules",
    "ProgressionTrees",
    "Unlocks",
    "LiveOpsStats",
]

# ---------------------------------------------------------------------------
# Common Steam install paths for Civ7
# ---------------------------------------------------------------------------
STEAM_PATHS = [
    # Windows
    r"C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VII",
    r"C:/Program Files/Steam/steamapps/common/Sid Meier's Civilization VII",
    r"D:/Steam/steamapps/common/Sid Meier's Civilization VII",
    r"D:/SteamLibrary/steamapps/common/Sid Meier's Civilization VII",
    r"E:/Steam/steamapps/common/Sid Meier's Civilization VII",
    r"E:/SteamLibrary/steamapps/common/Sid Meier's Civilization VII",
    # Linux
    os.path.expanduser("~/.steam/steam/steamapps/common/Sid Meier's Civilization VII"),
    os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization VII"),
    # macOS
    os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII"),
]


def find_game_dir() -> Path | None:
    """Auto-detect the Civ7 game directory from common Steam paths."""
    for path_str in STEAM_PATHS:
        path = Path(path_str)
        if path.is_dir():
            return path
    return None


def find_source_maps(game_dir: Path) -> list[Path]:
    """Find all .js.map files in the game directory."""
    maps = []
    for root, _dirs, files in os.walk(game_dir):
        for f in files:
            if f.endswith(".js.map"):
                maps.append(Path(root) / f)
    return maps


def extract_typescript_sources(map_files: list[Path]) -> list[str]:
    """Extract TypeScript source content from source map files."""
    sources = []
    errors = 0
    for map_file in map_files:
        try:
            with open(map_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            errors += 1
            continue

        for content in data.get("sourcesContent", []):
            if content and len(content) > 50:
                # Only include TypeScript-like content (skip HTML, CSS, etc.)
                if _looks_like_typescript(content):
                    sources.append(content)

    if errors:
        print(f"  Warning: {errors} map files had parse errors (skipped)")
    return sources


def _looks_like_typescript(content: str) -> bool:
    """Heuristic check if content looks like TypeScript/JavaScript."""
    # Skip HTML templates
    if content.strip().startswith(("<", "export default \"<")):
        return False
    # Skip CSS
    if content.strip().startswith(("@", ".")) and "{" in content[:200] and "function" not in content[:500]:
        return False
    # Accept anything with common TS/JS patterns
    indicators = ["function", "const ", "let ", "import ", "export ", "class ", "interface "]
    snippet = content[:1000]
    return any(ind in snippet for ind in indicators)


# ---------------------------------------------------------------------------
# Regex patterns for extraction
# ---------------------------------------------------------------------------

def _build_global_typed_call_pattern(global_name: str) -> re.Pattern:
    """Match typed Global.method(args) calls where the call is the direct RHS.

    Only captures return type when the method call is the complete assignment value,
    i.e. followed by a semicolon (not by operators like ==, +, ?, etc.).
    """
    return re.compile(
        r'(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+?)\s*=\s*'
        + re.escape(global_name)
        + r'\.([\w]+)\s*\(([^)]*)\)\s*[;\n]'
    )


def _build_global_call_pattern(global_name: str) -> re.Pattern:
    """Match Global.method(args) calls (without type extraction)."""
    return re.compile(
        re.escape(global_name)
        + r'\.([\w]+)\s*\(([^)]*)\)'
    )


def _build_global_property_pattern(global_name: str) -> re.Pattern:
    """Match Global.property access (no parens)."""
    # Matches: Global.prop (not followed by '(' which would be a method call)
    # The \b ensures we match the full identifier and don't backtrack into a
    # partial match of a method name (e.g. 'getGridWidt' from 'getGridWidth()')
    return re.compile(
        r'(?:(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+?)\s*=\s*)?'
        + re.escape(global_name)
        + r'\.([\w]+)\b(?!\s*\()'
    )


def _build_sub_object_typed_call_pattern(sub_name: str) -> re.Pattern:
    """Match typed *.SubObject.method(args) calls where the call is the direct RHS."""
    return re.compile(
        r'(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+?)\s*=\s*'
        r'\w+\.'
        + re.escape(sub_name)
        + r'\.([\w]+)\s*\(([^)]*)\)\s*[;\n]'
    )


def _build_sub_object_call_pattern(sub_name: str) -> re.Pattern:
    """Match *.SubObject.method(args) calls (without type extraction)."""
    # Matches patterns like:
    #   player.Cities.getCities()
    #   Game.Diplomacy.hasMet(id1, id2)
    #   p.Units.getUnits()
    return re.compile(
        r'\w+\.'
        + re.escape(sub_name)
        + r'\.([\w]+)\s*\(([^)]*)\)'
    )


def _build_sub_object_property_pattern(sub_name: str) -> re.Pattern:
    """Match *.SubObject.property access (no parens)."""
    return re.compile(
        r'(?:(?:const|let|var)\s+\w+\s*:\s*([\w\[\]|<>, ]+?)\s*=\s*)?'
        r'\w+\.'
        + re.escape(sub_name)
        + r'\.([\w]+)\b(?!\s*\()'
    )


def _extract_param_names(args_str: str) -> list[str]:
    """Extract parameter names from a call expression's argument list.

    For something like 'plotCoord.x, plotCoord.y' we return ['x', 'y'].
    For 'iX, iY' we return ['iX', 'iY'].
    For typed params like 'x: number, y: number' we return ['x', 'y'].
    """
    if not args_str.strip():
        return []

    params = []
    # Split by comma, handling nested braces/brackets
    depth = 0
    current = ""
    for ch in args_str:
        if ch in "({[":
            depth += 1
            current += ch
        elif ch in ")}]":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            params.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        params.append(current.strip())

    # Clean up parameter names
    clean_params = []
    for p in params:
        p = p.strip()
        if not p:
            continue

        # If it's a typed parameter (formal): 'name: Type'
        if ": " in p:
            name = p.split(":")[0].strip()
            # Remove optional marker
            name = name.rstrip("?")
            clean_params.append(name)
        else:
            # It's a call-site argument - try to get a meaningful name
            # Skip literals: strings, numbers, booleans, null/undefined
            if p.startswith('"') or p.startswith("'") or p.startswith("`"):
                clean_params.append("arg" + str(len(clean_params)))
            elif p in ("true", "false", "null", "undefined", "this"):
                clean_params.append("arg" + str(len(clean_params)))
            elif p.lstrip("-").replace(".", "", 1).isdigit():
                clean_params.append("arg" + str(len(clean_params)))
            # Remove property access chains: plotCoord.x -> x
            # Remove function calls: foo() -> skip
            # Remove array access: arr[i] -> skip
            # Remove object literals: { x: 1 } -> skip
            elif "{" in p or "[" in p or "(" in p:
                clean_params.append("arg" + str(len(clean_params)))
            elif "." in p:
                # Use the last part: plotCoord.x -> x
                parts = p.split(".")
                clean_params.append(parts[-1])
            # Skip ALL_CAPS constants (they're not param names)
            elif p.isupper() or (p.replace("_", "").isupper() and "_" in p):
                clean_params.append("arg" + str(len(clean_params)))
            # Skip ternary/conditional expressions
            elif "?" in p or "!" in p or "=" in p or ">" in p or "<" in p:
                clean_params.append("arg" + str(len(clean_params)))
            else:
                clean_params.append(p)

    return clean_params


def _clean_return_type(raw_type: str | None) -> str | None:
    """Clean up an extracted return type."""
    if not raw_type:
        return None
    t = raw_type.strip()
    # Remove null union: 'Type | null' -> 'Type'
    if " | null" in t:
        t = t.replace(" | null", "").strip()
    if " | undefined" in t:
        t = t.replace(" | undefined", "").strip()
    # Skip overly complex types
    if len(t) > 60:
        return None
    return t if t else None


def _merge_params(existing: list[str], new: list[str]) -> list[str]:
    """Merge parameter lists, preferring more descriptive names."""
    if not existing:
        return new
    if not new:
        return existing
    # If they have different lengths, prefer the longer one
    if len(new) > len(existing):
        return new
    if len(existing) > len(new):
        return existing
    # Same length - prefer names that are more descriptive (longer, not 'arg0')
    merged = []
    for e, n in zip(existing, new):
        if e.startswith("arg") and not n.startswith("arg"):
            merged.append(n)
        elif len(n) > len(e) and not n.startswith("arg"):
            merged.append(n)
        else:
            merged.append(e)
    return merged


def extract_members(
    sources: list[str],
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Extract global and sub-object members from TypeScript sources.

    Returns:
        (globals_dict, sub_objects_dict) where each dict maps name to
        {"methods": {...}, "properties": {...}}
    """
    globals_data: dict[str, dict] = {}
    sub_objects_data: dict[str, dict] = {}

    # Initialize structures
    for g in KNOWN_GLOBALS:
        globals_data[g] = {"methods": {}, "properties": {}}
    for s in KNOWN_SUB_OBJECTS:
        sub_objects_data[s] = {"methods": {}, "properties": {}}

    # Pre-compile patterns
    global_typed_call_patterns = {g: _build_global_typed_call_pattern(g) for g in KNOWN_GLOBALS}
    global_call_patterns = {g: _build_global_call_pattern(g) for g in KNOWN_GLOBALS}
    global_prop_patterns = {g: _build_global_property_pattern(g) for g in KNOWN_GLOBALS}
    sub_typed_call_patterns = {s: _build_sub_object_typed_call_pattern(s) for s in KNOWN_SUB_OBJECTS}
    sub_call_patterns = {s: _build_sub_object_call_pattern(s) for s in KNOWN_SUB_OBJECTS}
    sub_prop_patterns = {s: _build_sub_object_property_pattern(s) for s in KNOWN_SUB_OBJECTS}

    for source in sources:
        # --- Extract global methods (typed calls first for return types) ---
        for g_name, pattern in global_typed_call_patterns.items():
            for match in pattern.finditer(source):
                return_type = _clean_return_type(match.group(1))
                method_name = match.group(2)
                args_str = match.group(3)

                if method_name.startswith("_"):
                    continue

                params = _extract_param_names(args_str)
                methods = globals_data[g_name]["methods"]

                if method_name not in methods:
                    methods[method_name] = {
                        "params": params,
                        "return_type": return_type,
                    }
                else:
                    existing = methods[method_name]
                    existing["params"] = _merge_params(existing["params"], params)
                    if not existing["return_type"] and return_type:
                        existing["return_type"] = return_type

        # --- Extract global methods (untyped calls for method/param discovery) ---
        for g_name, pattern in global_call_patterns.items():
            for match in pattern.finditer(source):
                method_name = match.group(1)
                args_str = match.group(2)

                if method_name.startswith("_"):
                    continue

                params = _extract_param_names(args_str)
                methods = globals_data[g_name]["methods"]

                if method_name not in methods:
                    methods[method_name] = {
                        "params": params,
                        "return_type": None,
                    }
                else:
                    existing = methods[method_name]
                    existing["params"] = _merge_params(existing["params"], params)

        # --- Extract global properties ---
        for g_name, pattern in global_prop_patterns.items():
            for match in pattern.finditer(source):
                prop_type = _clean_return_type(match.group(1))
                prop_name = match.group(2)

                # Skip internal/private names
                if prop_name.startswith("_"):
                    continue
                # Skip if this is actually a known method (already captured with parens)
                if prop_name in globals_data[g_name]["methods"]:
                    continue
                # Skip if this is a known sub-object name
                if prop_name in KNOWN_SUB_OBJECTS:
                    continue

                props = globals_data[g_name]["properties"]
                if prop_name not in props:
                    props[prop_name] = {"type": prop_type}
                elif not props[prop_name]["type"] and prop_type:
                    props[prop_name]["type"] = prop_type

        # --- Extract sub-object methods (typed calls first) ---
        for s_name, pattern in sub_typed_call_patterns.items():
            for match in pattern.finditer(source):
                return_type = _clean_return_type(match.group(1))
                method_name = match.group(2)
                args_str = match.group(3)

                if method_name.startswith("_"):
                    continue

                params = _extract_param_names(args_str)
                methods = sub_objects_data[s_name]["methods"]

                if method_name not in methods:
                    methods[method_name] = {
                        "params": params,
                        "return_type": return_type,
                    }
                else:
                    existing = methods[method_name]
                    existing["params"] = _merge_params(existing["params"], params)
                    if not existing["return_type"] and return_type:
                        existing["return_type"] = return_type

        # --- Extract sub-object methods (untyped calls) ---
        for s_name, pattern in sub_call_patterns.items():
            for match in pattern.finditer(source):
                method_name = match.group(1)
                args_str = match.group(2)

                if method_name.startswith("_"):
                    continue

                params = _extract_param_names(args_str)
                methods = sub_objects_data[s_name]["methods"]

                if method_name not in methods:
                    methods[method_name] = {
                        "params": params,
                        "return_type": None,
                    }
                else:
                    existing = methods[method_name]
                    existing["params"] = _merge_params(existing["params"], params)

        # --- Extract sub-object properties ---
        for s_name, pattern in sub_prop_patterns.items():
            for match in pattern.finditer(source):
                prop_type = _clean_return_type(match.group(1))
                prop_name = match.group(2)

                if prop_name.startswith("_"):
                    continue
                if prop_name in sub_objects_data[s_name]["methods"]:
                    continue

                props = sub_objects_data[s_name]["properties"]
                if prop_name not in props:
                    props[prop_name] = {"type": prop_type}
                elif not props[prop_name]["type"] and prop_type:
                    props[prop_name]["type"] = prop_type

    # Clean up: remove empty entries
    globals_data = {
        k: v for k, v in globals_data.items()
        if v["methods"] or v["properties"]
    }
    sub_objects_data = {
        k: v for k, v in sub_objects_data.items()
        if v["methods"] or v["properties"]
    }

    # Clean up: remove properties that duplicate method names
    # (can happen due to regex overlap)
    for g_data in globals_data.values():
        for method_name in list(g_data["methods"]):
            g_data["properties"].pop(method_name, None)
    for s_data in sub_objects_data.values():
        for method_name in list(s_data["methods"]):
            s_data["properties"].pop(method_name, None)

    return globals_data, sub_objects_data


def build_completions(
    globals_data: dict[str, dict],
    sub_objects_data: dict[str, dict],
) -> dict:
    """Build the final completions.json structure."""
    return {
        "version": 1,
        "globals": globals_data,
        "sub_objects": sub_objects_data,
    }


def print_stats(completions: dict) -> None:
    """Print summary statistics about extracted data."""
    globals_data = completions["globals"]
    sub_objects_data = completions["sub_objects"]

    total_methods = 0
    total_props = 0

    print("\n  Globals:")
    for name in sorted(globals_data.keys()):
        g = globals_data[name]
        nm = len(g["methods"])
        np = len(g["properties"])
        total_methods += nm
        total_props += np
        typed_methods = sum(1 for m in g["methods"].values() if m.get("return_type"))
        print(f"    {name}: {nm} methods ({typed_methods} typed), {np} properties")

    print("\n  Sub-objects:")
    for name in sorted(sub_objects_data.keys()):
        s = sub_objects_data[name]
        nm = len(s["methods"])
        np = len(s["properties"])
        total_methods += nm
        total_props += np
        typed_methods = sum(1 for m in s["methods"].values() if m.get("return_type"))
        print(f"    {name}: {nm} methods ({typed_methods} typed), {np} properties")

    print(f"\n  Totals: {len(globals_data)} globals, {len(sub_objects_data)} sub-objects, "
          f"{total_methods} methods, {total_props} properties")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="civ7-extract-types",
        description="Extract TypeScript type data from Civ7 source maps for autocomplete",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--game-dir", "-g",
        type=str,
        default=None,
        help="Path to the Civ7 game directory (auto-detected if not specified)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="completions.json",
        help="Output file path for the completions JSON",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the extraction script."""
    args = parse_args()

    # --- Locate game directory ---
    if args.game_dir:
        game_dir = Path(args.game_dir)
        if not game_dir.is_dir():
            print(f"Error: Game directory not found: {game_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Auto-detecting Civ7 game directory...")
        game_dir = find_game_dir()
        if not game_dir:
            print(
                "Error: Could not auto-detect Civ7 game directory.\n"
                "Use --game-dir to specify the path manually.\n\n"
                "Common locations:\n"
                "  Windows: C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VII\n"
                "  Linux:   ~/.steam/steam/steamapps/common/Sid Meier's Civilization VII\n"
                "  macOS:   ~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VII",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Game directory: {game_dir}")

    # --- Find source maps ---
    print("Scanning for .js.map files...")
    start_time = time.time()
    map_files = find_source_maps(game_dir)
    print(f"  Found {len(map_files)} source map files")

    if not map_files:
        print("Error: No .js.map files found in the game directory.", file=sys.stderr)
        sys.exit(1)

    # --- Extract TypeScript sources ---
    print("Extracting TypeScript sources...")
    sources = extract_typescript_sources(map_files)
    total_size = sum(len(s) for s in sources)
    print(f"  Extracted {len(sources)} TypeScript sources ({total_size / 1024 / 1024:.1f} MB)")

    # --- Parse members ---
    print("Parsing type signatures...")
    globals_data, sub_objects_data = extract_members(sources)

    # --- Build and write output ---
    completions = build_completions(globals_data, sub_objects_data)

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(completions, f, indent=2, sort_keys=False)

    elapsed = time.time() - start_time
    print(f"\nWrote {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    print_stats(completions)
    print(f"\nCompleted in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
