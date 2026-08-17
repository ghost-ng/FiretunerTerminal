"""Helpers behind the higher-level MCP tools: connection diagnosis, canned JS
payloads for game state / UI automation, log reading, and map rendering.

The JS payloads implement the proven patterns from test-harness/ (engine-input
button presses, JSON.stringify'd single-expression results).
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Optional

CDP_PORT = 9444  # Cohtml UI debugger; stays open during MP tuner suspension

FIRAXIS_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Firaxis Games" / "Sid Meier's Civilization VII"
LOGS_DIR = FIRAXIS_DIR / "Logs"
APP_OPTIONS = FIRAXIS_DIR / "AppOptions.txt"


# ---------------------------------------------------------------------------
# Connection diagnosis (#2)
# ---------------------------------------------------------------------------

def _port_open(port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _enable_tuner_setting() -> Optional[str]:
    """Return the EnableTuner value from AppOptions.txt, or None if unknown."""
    try:
        for line in APP_OPTIONS.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("EnableTuner"):
                return line.split()[-1]
    except OSError:
        pass
    return None


def _game_window_present() -> bool:
    from .screenshot import _find_game_window
    return _find_game_window() is not None


def diagnose_disconnect() -> str:
    """Explain WHY the tuner port is unreachable, in order of likelihood."""
    if not _game_window_present():
        return "Civ 7 does not appear to be running (no game window found). Start the game."
    setting = _enable_tuner_setting()
    if setting is not None and setting != "1":
        return (
            f"Civ 7 is running but EnableTuner is '{setting}' in AppOptions.txt "
            "(needs to be 1, then restart the game). File: " + str(APP_OPTIONS)
        )
    if _port_open(CDP_PORT):
        return (
            "Civ 7 is running with the tuner enabled, but the tuner port is closed — "
            "the game suspends it during multiplayer/hotseat sessions (the UI debugger "
            f"on port {CDP_PORT} is still up, which confirms the game is alive). "
            "It reopens when the game returns to the main menu."
        )
    return (
        "Civ 7 appears to be running but the tuner port is closed and the cause is "
        "unclear. If the game just launched, wait for the main menu; otherwise check "
        "EnableTuner in AppOptions.txt and restart the game."
    )


# ---------------------------------------------------------------------------
# Log reading (#5)
# ---------------------------------------------------------------------------

MAX_LOG_CHARS = 50_000


def read_log(name: str = "", tail_lines: int = 100, grep: str = "") -> str:
    """List available logs (empty name) or return the tail of one, optionally filtered."""
    if not LOGS_DIR.is_dir():
        return f"ERROR: Logs directory not found: {LOGS_DIR}"

    if not name:
        rows = []
        for p in sorted(LOGS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if p.is_file():
                st = p.stat()
                rows.append(f"{p.name}  ({st.st_size} bytes, modified {st.st_mtime:.0f})")
        return "Available logs (newest first):\n" + "\n".join(rows)

    path = (LOGS_DIR / name).resolve()
    if LOGS_DIR.resolve() not in path.parents:
        return "ERROR: log name must be a plain filename inside the Logs directory"
    if not path.is_file():
        return f"ERROR: no such log: {name}. Call with no name to list logs."

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if grep:
        lines = [ln for ln in lines if grep.lower() in ln.lower()]
    lines = lines[-max(1, tail_lines):]
    out = "\n".join(lines)
    if len(out) > MAX_LOG_CHARS:
        out = out[-MAX_LOG_CHARS:]
        out = "...(truncated)...\n" + out[out.index("\n") + 1:]
    return out or "(no matching lines)"


# ---------------------------------------------------------------------------
# JS payloads (#3, #6) — every payload is a single expression returning a
# JSON.stringify'd result, per the tuner protocol's rules.
# ---------------------------------------------------------------------------

# Shared helper injected into payloads that press buttons (engine-input
# START/FINISH pair on the element itself; synthetic clicks are ignored).
_PRESS_FN = """
const __press = (el) => {
  const mk = (status) => new CustomEvent('engine-input', {
    bubbles: true, cancelable: true,
    detail: { name: 'mousebutton-left', status, x: -1, y: -1,
              isTouch: false, isMouse: true }
  });
  el.dispatchEvent(mk(InputActionStatuses.START));
  el.dispatchEvent(mk(InputActionStatuses.FINISH));
};
"""

GET_SCREEN_JS = """
(() => {
  const txt = (el) => (el.textContent || '').trim();
  const stack = Array.from(document.querySelectorAll('.fullscreen > *')).map(e => e.tagName);
  const hero = Array.from(document.querySelectorAll('div.hero-button-2')).map(txt).filter(Boolean);
  const activatable = Array.from(document.querySelectorAll('[data-activatable="true"]'))
    .map(txt).filter(Boolean).slice(0, 60);
  const buttons = Array.from(document.querySelectorAll('fxs-text-button, fxs-button, .fxs-button'))
    .map(txt).filter(Boolean).slice(0, 60);
  const dialog = (document.querySelector('screen-dialog-box')?.textContent || '').trim() || null;
  return JSON.stringify({
    inGame: UI.isInGame(),
    screenStack: stack,
    heroButtons: hero,
    activatable: [...new Set(activatable)],
    otherButtons: [...new Set(buttons)],
    dialog
  }, null, 1);
})()
"""


def press_button_js(caption: str) -> str:
    """Payload that finds a button by caption (case-insensitive) and presses it."""
    cap = json.dumps(caption)
    return (
        "(() => {" + _PRESS_FN + f"""
  const want = {cap}.trim().toLowerCase();
  const candidates = Array.from(document.querySelectorAll(
    'div.hero-button-2, [data-activatable="true"], fxs-text-button, fxs-button, .fxs-button'));
  const labeled = candidates.map(el => ({{el, t: (el.textContent || '').trim()}}))
    .filter(c => c.t);
  const hit = labeled.find(c => c.t.toLowerCase() === want)
           || labeled.find(c => c.t.toLowerCase().includes(want));
  if (!hit) return JSON.stringify({{pressed: false,
    available: [...new Set(labeled.map(c => c.t))].slice(0, 60)}});
  __press(hit.el);
  return JSON.stringify({{pressed: true, caption: hit.t}});
}})()"""
    )


# get_game_state sections: each is (js-fragment producing a value, key)
_STATE_SECTIONS = {
    "overview": """{
      turn: Game.turn, age: Game.age, maxTurns: Game.maxTurns,
      turnDate: (Game.getTurnDate ? Game.getTurnDate() : null)
    }""",
    "players": """Players.getAliveMajorIds().map(id => {
      const p = Players.get(id);
      return {
        id, civ: (typeof Locale !== "undefined" ? Locale.compose(p.civilizationFullName) : p.civilizationFullName), leader: p.leaderName ?? p.leaderType,
        isHuman: p.isHuman, gold: p.Treasury ? p.Treasury.goldBalance : null,
        researching: p.Techs?.getResearching?.()?.type ?? null,
        cityCount: p.Cities ? p.Cities.getCities().length : 0,
        unitCount: p.Units ? p.Units.getUnits().length : 0
      };
    })""",
    "cities": """Players.getAliveMajorIds().flatMap(id => {
      const p = Players.get(id);
      return (p.Cities ? p.Cities.getCities() : []).map(c => ({
        owner: id, name: (typeof Locale !== "undefined" ? Locale.compose(c.name) : c.name), x: c.location.x, y: c.location.y,
        population: c.population, isCapital: c.isCapital
      }));
    })""",
    "units": """Players.getAliveMajorIds().flatMap(id => {
      const p = Players.get(id);
      return (p.Units ? p.Units.getUnits() : []).map(u => ({
        owner: id, type: u.type, name: u.name,
        x: u.location.x, y: u.location.y
      }));
    })""",
    "map": """{
      width: GameplayMap.getGridWidth(), height: GameplayMap.getGridHeight(),
      mapType: (Configuration.getMap()?.getValue?.('Name') ?? null)
    }""",
}


def get_game_state_js(sections: list[str]) -> str:
    parts = ",\n".join(f'"{k}": ({_STATE_SECTIONS[k]})' for k in sections)
    return (
        """(() => {
  if (!UI.isInGame()) {
    const stack = Array.from(document.querySelectorAll('.fullscreen > *')).map(e => e.tagName);
    return JSON.stringify({inGame: false, screenStack: stack,
      note: 'Not in a game - only screen info available. Use get_screen/press_button to navigate.'});
  }
  const state = {inGame: true,
""" + parts + """
  };
  return JSON.stringify(state, (k, v) => typeof v === 'bigint' ? v.toString() : v);
})()"""
    )


def reveal_map_js(scope: str) -> str:
    """Payload revealing all plots — same mechanism as Firaxis's Map tuner panel
    (Visibility.revealAllPlots, WorldBuilder fallback). scope: 'human' | 'all' |
    a numeric player id as a string."""
    scope_js = json.dumps(scope)
    return (
        """(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const scope = """ + scope_js + """;
  const ids = Players.getAliveMajorIds().filter(id => {
    if (scope === 'all') return true;
    if (scope === 'human') return Players.get(id).isHuman;
    return String(id) === scope;
  });
  const revealed = [];
  for (const id of ids) {
    if (typeof Visibility !== 'undefined' && Visibility.revealAllPlots) {
      Visibility.revealAllPlots(id);
    } else {
      WorldBuilder.MapPlots.setAllRevealed(id, true);
    }
    revealed.push(id);
  }
  return JSON.stringify({
    revealedFor: revealed,
    note: revealed.length ? undefined :
      "no players matched scope '" + scope + "' (autoplay games have no humans - use scope 'all' or a player id)"
  });
})()"""
    )


LIST_CIVS_UNITS_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const civs = Players.getAliveMajorIds().map(id => {
    const p = Players.get(id);
    const units = (p.Units ? p.Units.getUnits() : []).map(u => {
      const info = GameInfo.Units.lookup(u.type);
      return {
        name: L(u.name), type: info ? info.UnitType : String(u.type),
        x: u.location.x, y: u.location.y,
        damage: (u.Health && typeof u.Health.damage === 'number') ? u.Health.damage : undefined
      };
    });
    const unitCounts = {};
    units.forEach(u => { unitCounts[u.type] = (unitCounts[u.type] || 0) + 1; });
    return {
      id,
      civ: L(p.civilizationFullName),
      leader: L(p.leaderName ?? p.leaderType),
      isHuman: p.isHuman,
      gold: p.Treasury ? Math.round(p.Treasury.goldBalance) : null,
      cities: p.Cities ? p.Cities.getCities().map(c => L(c.name)) : [],
      unitTotal: units.length,
      unitCounts,
      units
    };
  });
  return JSON.stringify({turn: Game.turn, civs},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


# render_map tile dump: compact int arrays + legends built from GameInfo, so
# the Python side needs no hardcoded type IDs.
MAP_DUMP_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  const terrain = [], biome = [], feature = [], owner = [];
  const tLegend = {}, bLegend = {}, fLegend = {};
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const t = GameplayMap.getTerrainType(x, y);
      const b = GameplayMap.getBiomeType(x, y);
      const f = GameplayMap.getFeatureType(x, y);
      terrain.push(t); biome.push(b); feature.push(f);
      owner.push(GameplayMap.getOwner(x, y));
      if (!(t in tLegend)) tLegend[t] = GameInfo.Terrains.lookup(t)?.TerrainType ?? String(t);
      if (!(b in bLegend)) bLegend[b] = GameInfo.Biomes.lookup(b)?.BiomeType ?? String(b);
      if (f !== -1 && !(f in fLegend)) fLegend[f] = GameInfo.Features.lookup(f)?.FeatureType ?? String(f);
    }
  }
  const cities = Players.getAliveMajorIds().flatMap(id => {
    const p = Players.get(id);
    return (p.Cities ? p.Cities.getCities() : []).map(c => ({
      owner: id, name: (typeof Locale !== "undefined" ? Locale.compose(c.name) : c.name), x: c.location.x, y: c.location.y, capital: c.isCapital
    }));
  });
  const units = Players.getAliveMajorIds().flatMap(id => {
    const p = Players.get(id);
    return (p.Units ? p.Units.getUnits() : []).map(u => ({owner: id, x: u.location.x, y: u.location.y}));
  });
  return JSON.stringify({w, h, terrain, biome, feature, owner,
    tLegend, bLegend, fLegend, cities, units});
})()
"""


# ---------------------------------------------------------------------------
# Map rendering (#4)
# ---------------------------------------------------------------------------

_BIOME_COLORS = {
    "GRASSLAND": (110, 150, 70), "PLAINS": (170, 160, 90), "DESERT": (215, 185, 130),
    "TUNDRA": (180, 185, 170), "TROPICAL": (60, 120, 60), "MARINE": (70, 110, 165),
}
_PLAYER_COLORS = [
    (230, 60, 60), (60, 120, 230), (240, 200, 60), (150, 70, 200), (60, 200, 200),
    (240, 130, 40), (110, 220, 90), (230, 110, 180), (140, 100, 60), (200, 200, 200),
]


def _tile_color(t_name: str, b_name: str) -> tuple[int, int, int]:
    if "OCEAN" in t_name:
        return (40, 70, 120)
    if "COAST" in t_name:
        return (80, 130, 180)
    if "NAVIGABLE_RIVER" in t_name:
        return (90, 150, 190)
    base = (120, 140, 90)
    for key, color in _BIOME_COLORS.items():
        if key in b_name:
            base = color
            break
    if "MOUNTAIN" in t_name:
        return (120, 115, 110)
    if "HILL" in t_name:
        return tuple(max(0, c - 35) for c in base)
    return base


def render_map_png(dump: dict, tile_px: int = 12) -> bytes:
    """Render the MAP_DUMP_JS result to a PNG (hex-staggered tiles + legend)."""
    from PIL import Image, ImageDraw

    w, h = dump["w"], dump["h"]
    t_leg = {int(k): v for k, v in dump["tLegend"].items()}
    b_leg = {int(k): v for k, v in dump["bLegend"].items()}
    f_leg = {int(k): v for k, v in dump.get("fLegend", {}).items()}

    stagger = tile_px // 2
    img_w = w * tile_px + stagger + 2
    legend_h = 58
    img_h = h * tile_px + legend_h
    img = Image.new("RGB", (img_w, img_h), (25, 25, 30))
    draw = ImageDraw.Draw(img)

    def tile_xy(x: int, y: int) -> tuple[int, int]:
        # Hex grid: odd rows offset half a tile; y flipped (game y=0 is south)
        px = x * tile_px + (stagger if y % 2 else 0)
        py = (h - 1 - y) * tile_px
        return px, py

    for y in range(h):
        for x in range(w):
            i = y * w + x
            t_name = t_leg.get(dump["terrain"][i], "")
            b_name = b_leg.get(dump["biome"][i], "")
            color = _tile_color(t_name, b_name)
            f = dump["feature"][i]
            f_name = f_leg.get(f, "") if f != -1 else ""
            if "FOREST" in f_name or "JUNGLE" in f_name or "TAIGA" in f_name:
                color = tuple(max(0, c - 25) for c in color)
            px, py = tile_xy(x, y)
            draw.rectangle([px, py, px + tile_px - 1, py + tile_px - 1], fill=color)
            own = dump["owner"][i]
            if own >= 0 and own < len(_PLAYER_COLORS):
                draw.rectangle([px, py, px + tile_px - 1, py + tile_px - 1],
                               outline=_PLAYER_COLORS[own % len(_PLAYER_COLORS)], width=1)

    for u in dump.get("units", []):
        px, py = tile_xy(u["x"], u["y"])
        c = _PLAYER_COLORS[u["owner"] % len(_PLAYER_COLORS)]
        m = tile_px // 2
        draw.polygon([(px + m, py + 2), (px + 2, py + tile_px - 3),
                      (px + tile_px - 3, py + tile_px - 3)], fill=c, outline=(0, 0, 0))

    for c in dump.get("cities", []):
        px, py = tile_px // 2 + tile_xy(c["x"], c["y"])[0], tile_px // 2 + tile_xy(c["x"], c["y"])[1]
        col = _PLAYER_COLORS[c["owner"] % len(_PLAYER_COLORS)]
        r = tile_px // 2 + (2 if c.get("capital") else 0)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=col, outline=(255, 255, 255), width=2)
        draw.text((px + r + 2, py - 6), c["name"], fill=(255, 255, 255))

    ly = h * tile_px + 6
    draw.text((6, ly), "water/land colors = terrain+biome | outlines = tile owner | "
                       "circles = cities (white ring; big = capital) | triangles = units",
              fill=(220, 220, 220))
    lx = 6
    for pid in sorted({c["owner"] for c in dump.get("cities", [])} |
                      {u["owner"] for u in dump.get("units", [])}):
        col = _PLAYER_COLORS[pid % len(_PLAYER_COLORS)]
        draw.rectangle([lx, ly + 20, lx + 12, ly + 32], fill=col)
        draw.text((lx + 16, ly + 20), f"P{pid}", fill=(220, 220, 220))
        lx += 58

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
