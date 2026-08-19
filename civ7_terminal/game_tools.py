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

from .cdp import CDP_PORT  # Cohtml UI debugger; stays open during MP tuner suspension

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


def diagnose_disconnect(tuner_port: int = 4318) -> str:
    """Explain WHY the tuner port is unreachable, in order of likelihood."""
    if _port_open(tuner_port):
        return (
            "The tuner port is actually open — the connection is likely mid-reconnect "
            "(it retries with backoff, up to 30s). Retry in a few seconds."
        )
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
            "Commands normally auto-fall back to CDP on that port; seeing this error "
            "means the CDP evaluation itself failed — retry, or wait for the game to "
            "return to the main menu, which reopens the tuner."
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
# Save files
# ---------------------------------------------------------------------------

# Local save roots to try; with Steam Cloud saves enabled there may be none.
_SAVE_DIRS = [
    FIRAXIS_DIR / "Saves",
    Path(os.environ.get("USERPROFILE", "")) / "Documents" / "My Games"
    / "Sid Meier's Civilization VII" / "Saves",
]


def list_saves() -> str:
    """List local save files (newest first) from the game's save directories."""
    rows = []
    for root in _SAVE_DIRS:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.is_file():
                st = p.stat()
                rows.append((st.st_mtime, f"{p.relative_to(root)}  ({st.st_size} bytes)"))
    if not rows:
        return (
            "No local save files found (checked: "
            + "; ".join(str(d) for d in _SAVE_DIRS)
            + "). Saves are likely in Steam Cloud (SaveLocations.STEAM_CLOUD), "
            "which has no local directory to list."
        )
    rows.sort(reverse=True)
    import datetime
    lines = [f"{datetime.datetime.fromtimestamp(m):%Y-%m-%d %H:%M}  {r}" for m, r in rows[:60]]
    return "Local saves (newest first):\n" + "\n".join(lines)


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


DESCRIBE_SCREEN_JS = """
(() => {
  const txt = (el) => (el.textContent || '').trim();
  const vis = (el) => el.offsetParent !== null;

  // Screen composition: what's mounted, collapsed to counts
  const counts = {};
  Array.from(document.querySelectorAll('.fullscreen > *')).forEach(e => {
    counts[e.tagName] = (counts[e.tagName] || 0) + 1;
  });

  // Visible headings / labels — what a human would read to orient themselves
  const labels = [...new Set(
    Array.from(document.querySelectorAll(
      'fxs-header, [class*="title"], [class*="header"], h1, h2, h3'))
      .filter(vis).map(txt).filter(t => t && t.length < 80)
  )].slice(0, 30);

  // Pressable things (same sources as press_button)
  const buttons = [...new Set(
    Array.from(document.querySelectorAll(
      'div.hero-button-2, [data-activatable="true"], fxs-text-button, fxs-button, .fxs-button'))
      .filter(vis).map(txt).filter(Boolean)
  )].slice(0, 40);

  const dialog = (document.querySelector('screen-dialog-box')?.textContent || '').trim() || null;

  const inGame = UI.isInGame();
  const context = {inGame};
  if (inGame && typeof Game !== 'undefined') {
    context.turn = Game.turn;
    context.turnDate = Game.getTurnDate ? Game.getTurnDate() : null;
  }

  return JSON.stringify({
    context,
    screenComposition: counts,
    visibleLabels: labels,
    pressableButtons: buttons,
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


GET_CONTINENTS_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  const tiles = {};
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const c = GameplayMap.getContinentType(x, y);
    if (c !== -1) tiles[c] = (tiles[c] || 0) + 1;
  }
  const cities = Players.getAliveMajorIds().flatMap(id => {
    const p = Players.get(id);
    return (p.Cities ? p.Cities.getCities() : []).map(c => ({
      owner: id, name: L(c.name), x: c.location.x, y: c.location.y}));
  });
  const continents = Object.keys(tiles).map(Number).map(id => {
    const info = GameInfo.Continents.lookup(id);
    const cs = cities.filter(c => GameplayMap.getContinentType(c.x, c.y) === id);
    return {
      id,
      type: info ? info.ContinentType : String(id),
      name: info && info.Description ? L(info.Description) : null,
      tiles: tiles[id],
      cityCount: cs.length,
      playersPresent: [...new Set(cs.map(c => c.owner))],
      cities: cs.map(c => c.name)
    };
  });
  return JSON.stringify({continentCount: continents.length, continents},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


GET_PLAYERS_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const majors = Players.getAliveMajorIds();
  const players = majors.map(id => {
    const p = Players.get(id);
    const capital = p.Cities && p.Cities.getCapital ? p.Cities.getCapital() : null;
    let government = null;
    try {
      const g = GameInfo.Governments.lookup(p.Culture.getGovernmentType());
      government = g ? g.GovernmentType : null;
    } catch (e) { /* pre-government age */ }
    const others = majors.filter(o => o !== id);
    return {
      id,
      civ: L(p.civilizationFullName),
      leader: L(p.leaderName ?? p.leaderType),
      isHuman: p.isHuman,
      team: p.team,
      gold: p.Treasury ? Math.round(p.Treasury.goldBalance) : null,
      government,
      cityCount: p.Cities ? p.Cities.getCities().length : 0,
      capital: capital ? L(capital.name) : null,
      unitCount: p.Units ? p.Units.getUnits().length : 0,
      met: others.filter(o => Game.Diplomacy.hasMet(id, o)),
      atWarWith: others.filter(o => p.Diplomacy && p.Diplomacy.isAtWarWith(o))
    };
  });
  return JSON.stringify({
    turn: Game.turn,
    majorCount: players.length,
    players,
    independentIds: Players.getAliveIndependentIds()
  }, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


GET_CITYSTATES_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const IP = Game.IndependentPowers;
  const majors = Players.getAliveMajorIds();
  // Village/settlement plot per independent. getIndependentPlayerIDAt also
  // reports non-independent ids on owned plots, so filter by id later.
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  const plots = {};
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const pid = IP.getIndependentPlayerIDAt(x, y);
    if (pid >= 0 && plots[pid] === undefined) plots[pid] = {x, y};
  }
  const independents = Players.getAliveIndependentIds().map(id => {
    const p = Players.get(id);
    let cityStateType = null;
    try { cityStateType = p.getCityStateCityStateType ? p.getCityStateCityStateType() : null; }
    catch (e) { /* leave null */ }
    const relationshipToMajors = {};
    majors.forEach(m => {
      try { relationshipToMajors[m] = L(IP.getIndependentHostility(id, m)); }
      catch (e) { /* skip */ }
    });
    let suzerainBonusChosen = null, bonusType = null;
    try { suzerainBonusChosen = Game.CityStates.hasBeenChosen(cityStateType); } catch (e) {}
    try { bonusType = Game.CityStates.getBonusType(cityStateType); } catch (e) {}
    return {
      id,
      name: L(IP.independentName(id)),
      encampment: IP.isIndependentEncampment(id),
      plot: plots[id] ?? null,
      unitCount: p.Units ? p.Units.getUnits().length : 0,
      cityCount: p.Cities ? p.Cities.getCities().length : 0,
      cityStateType,
      suzerainBonusChosen,
      bonusType,
      relationshipToMajors
    };
  });
  return JSON.stringify({independentCount: independents.length, independents},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


GET_CONTINENT_SIZE_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  const stats = {};
  let land = 0, water = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (GameplayMap.isWater(x, y)) { water++; continue; }
    land++;
    const c = GameplayMap.getContinentType(x, y);
    if (c === -1) continue;
    const s = stats[c] ?? (stats[c] = {tiles: 0, minX: x, maxX: x, minY: y, maxY: y});
    s.tiles++;
    if (x < s.minX) s.minX = x; if (x > s.maxX) s.maxX = x;
    if (y < s.minY) s.minY = y; if (y > s.maxY) s.maxY = y;
  }
  const continents = Object.keys(stats).map(Number).map(id => {
    const s = stats[id];
    const info = GameInfo.Continents.lookup(id);
    return {
      id,
      type: info ? info.ContinentType : String(id),
      tiles: s.tiles,
      pctOfLand: Math.round(1000 * s.tiles / land) / 10,
      pctOfMap: Math.round(1000 * s.tiles / (w * h)) / 10,
      boundingBox: {minX: s.minX, maxX: s.maxX, minY: s.minY, maxY: s.maxY,
                    width: s.maxX - s.minX + 1, height: s.maxY - s.minY + 1}
    };
  }).sort((a, b) => b.tiles - a.tiles);
  return JSON.stringify({
    map: {width: w, height: h, landTiles: land, waterTiles: water,
          waterPct: Math.round(1000 * water / (w * h)) / 10},
    continents
  }, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


GET_AGE_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const info = GameInfo.Ages.lookup(Game.age);
  let progress = null;
  try {
    const M = Game.AgeProgressManager;
    progress = {
      current: M.getCurrentAgeProgressionPoints(),
      max: M.getMaxAgeProgressionPoints(),
      isAgeOver: M.isAgeOver,
      countdownStarted: M.ageCountdownStarted
    };
  } catch (e) { /* leave null */ }
  return JSON.stringify({
    age: info ? info.AgeType : String(Game.age),
    name: info ? L(info.Name) : null,
    chronologyIndex: info ? info.ChronologyIndex : null,
    turn: Game.turn,
    maxTurns: Game.maxTurns,
    turnDate: Game.getTurnDate ? Game.getTurnDate() : null,
    progress
  }, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()
"""


def get_map_resources_js(include_locations: bool) -> str:
    """Payload scanning every tile's resource; counts per type, optional plots."""
    with_locs = "true" if include_locations else "false"
    return (
        """(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const withLocs = """ + with_locs + """;
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  const byType = {};
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const r = GameplayMap.getResourceType(x, y);
    if (r === -1) continue;
    if (!byType[r]) {
      const info = GameInfo.Resources.lookup(r);
      byType[r] = {
        type: info ? info.ResourceType : String(r),
        name: info ? L(info.Name) : null,
        class: info ? info.ResourceClassType : null,
        count: 0
      };
      if (withLocs) byType[r].tiles = [];
    }
    byType[r].count++;
    if (withLocs) byType[r].tiles.push({x, y});
  }
  const resources = Object.values(byType).sort((a, b) => b.count - a.count);
  return JSON.stringify({
    totalResourceTiles: resources.reduce((s, r) => s + r.count, 0),
    typeCount: resources.length,
    resources
  }, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
    )


def get_player_resources_js(player_id: int) -> str:
    """Payload listing one player's (or every major's, for -1) resources."""
    pid = str(int(player_id))
    return (
        """(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const want = """ + pid + """;
  const w = GameplayMap.getGridWidth();
  const ids = want === -1 ? Players.getAliveMajorIds()
    : (Players.isAlive(want) ? [want] : []);
  if (!ids.length) return JSON.stringify({error: 'no such alive player: ' + want});
  const players = ids.map(id => {
    const p = Players.get(id);
    const R = p.Resources;
    if (!R) return {id, error: 'no Resources object'};
    const items = (R.getResources() || []).map(e => {
      const hash = e.uniqueResource ? e.uniqueResource.resource : e;
      const info = GameInfo.Resources.lookup(hash);
      const item = {
        type: info ? info.ResourceType : String(hash),
        name: info ? L(info.Name) : null,
        class: info ? info.ResourceClassType : null
      };
      if (typeof e.value === 'number') {
        item.plot = {x: e.value % w, y: Math.floor(e.value / w)};
        try {
          const cid = R.getCityIDAssigned(e.value);
          if (cid && cid.id !== undefined && cid.id !== -1) item.assignedCityId = cid.id;
        } catch (err) { /* unassigned */ }
      }
      return item;
    });
    const countsByType = {};
    items.forEach(i => { countsByType[i.type] = (countsByType[i.type] || 0) + 1; });
    return {
      id, civ: L(p.civilizationFullName),
      total: items.length,
      toAssign: R.getCountResourcesToAssign(),
      imported: R.getCountImportedResources(),
      countsByType,
      resources: items
    };
  });
  return JSON.stringify(want === -1 ? {players} : players[0],
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
    )


# Shared JS helpers injected into the deep-inspection payloads below.
_COMMON_FNS = """
  const L = (s) => (typeof Locale !== 'undefined' && s) ? Locale.compose(s) : s;
  const lookupName = (hash) => {
    for (const tbl of ['Constructibles', 'Units', 'Projects', 'ProgressionTreeNodes', 'Techs']) {
      try {
        const info = GameInfo[tbl] && GameInfo[tbl].lookup ? GameInfo[tbl].lookup(hash) : null;
        if (info) return info.ConstructibleType ?? info.UnitType ?? info.ProjectType
                    ?? info.ProgressionTreeNodeType ?? info.TechType ?? String(hash);
      } catch (e) { /* next table */ }
    }
    return String(hash);
  };
  const yieldTypes = [...GameInfo.Yields].map(y => ({type: y.YieldType, hash: y.$hash}));
"""


def get_tile_js(x: int, y: int) -> str:
    """Payload describing everything about one plot."""
    xs, ys = str(int(x)), str(int(y))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const x = {xs}, y = {ys};
  if (x < 0 || y < 0 || x >= GameplayMap.getGridWidth() || y >= GameplayMap.getGridHeight())
    return JSON.stringify({{error: 'out of bounds', width: GameplayMap.getGridWidth(), height: GameplayMap.getGridHeight()}});
  const t = GameplayMap.getTerrainType(x, y), b = GameplayMap.getBiomeType(x, y);
  const f = GameplayMap.getFeatureType(x, y), r = GameplayMap.getResourceType(x, y);
  const cont = GameplayMap.getContinentType(x, y);
  const contInfo = cont !== -1 ? GameInfo.Continents.lookup(cont) : null;
  const owner = GameplayMap.getOwner(x, y);
  let city = null;
  for (const id of Players.getAliveIds()) {{
    const p = Players.get(id);
    const hit = (p.Cities ? p.Cities.getCities() : []).find(c => c.location.x === x && c.location.y === y);
    if (hit) {{ city = {{name: L(hit.name), owner: id, isCapital: hit.isCapital, isTown: hit.isTown}}; break; }}
  }}
  const units = Players.getAliveIds().flatMap(id => {{
    const p = Players.get(id);
    return (p.Units ? p.Units.getUnits() : []).filter(u => u.location.x === x && u.location.y === y)
      .map(u => ({{owner: id, name: L(u.name), type: u.typeName}}));
  }});
  return JSON.stringify({{
    x, y,
    terrain: GameInfo.Terrains.lookup(t)?.TerrainType ?? String(t),
    biome: GameInfo.Biomes.lookup(b)?.BiomeType ?? String(b),
    feature: f !== -1 ? (GameInfo.Features.lookup(f)?.FeatureType ?? String(f)) : null,
    resource: r !== -1 ? (GameInfo.Resources.lookup(r)?.ResourceType ?? String(r)) : null,
    continent: contInfo ? contInfo.ContinentType : null,
    owner: owner >= 0 ? owner : null,
    city, units,
    elevation: GameplayMap.getElevation(x, y),
    isImpassable: GameplayMap.isImpassable(x, y),
    isLake: GameplayMap.isLake(x, y),
    isFreshWater: GameplayMap.isFreshWater(x, y),
    isNaturalWonder: GameplayMap.isNaturalWonder(x, y),
    isRiver: GameplayMap.isRiver(x, y),
    isNavigableRiver: GameplayMap.isNavigableRiver(x, y),
    riverName: (() => {{ try {{ return GameplayMap.getRiverName(x, y) || null; }} catch (e) {{ return null; }} }})()
  }}, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_city_js(x: int, y: int) -> str:
    """Payload with deep detail for the city at a plot."""
    xs, ys = str(int(x)), str(int(y))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const x = {xs}, y = {ys};
  let city = null, ownerId = null;
  for (const id of Players.getAliveIds()) {{
    const p = Players.get(id);
    const hit = (p.Cities ? p.Cities.getCities() : []).find(c => c.location.x === x && c.location.y === y);
    if (hit) {{ city = hit; ownerId = id; break; }}
  }}
  if (!city) return JSON.stringify({{error: 'no city at (' + x + ',' + y + ') — use get_game_state sections=cities for locations'}});
  const yields = {{}};
  yieldTypes.forEach(yt => {{
    try {{ yields[yt.type] = city.Yields.getNetYield(yt.hash); }} catch (e) {{ /* skip */ }}
  }});
  const buildings = (() => {{ try {{
    return city.Constructibles.getIds().map(cid => {{
      const inst = Constructibles.get(cid);
      return inst ? {{type: inst.typeName, complete: inst.complete, damaged: inst.damaged,
                     x: inst.location.x, y: inst.location.y}} : null;
    }}).filter(Boolean);
  }} catch (e) {{ return []; }} }})();
  const bq = city.BuildQueue;
  return JSON.stringify({{
    name: L(city.name), owner: ownerId, location: {{x, y}},
    isCapital: city.isCapital, isTown: city.isTown, isOriginalCapital: city.isOriginalCapital,
    isBeingRazed: city.isBeingRazed, isDistantLands: city.isDistantLands,
    population: city.population, urbanPopulation: city.urbanPopulation, ruralPopulation: city.ruralPopulation,
    growth: (() => {{ try {{ return {{turnsUntilGrowth: city.Growth.turnsUntilGrowth,
      currentFood: city.Growth.currentFood, growthRate: city.Growth.growthRate}}; }} catch (e) {{ return null; }} }})(),
    happiness: (() => {{ try {{ return {{netPerTurn: city.Happiness.netHappinessPerTurn,
      hasUnrest: city.Happiness.hasUnrest, turnsOfUnrest: city.Happiness.turnsOfUnrest}}; }} catch (e) {{ return null; }} }})(),
    netYields: yields,
    producing: bq.isEmpty ? null : {{item: lookupName(bq.currentProductionTypeHash),
      turnsLeft: bq.currentTurnsLeft, percentComplete: (() => {{ try {{ return bq.getPercentComplete(bq.currentProductionTypeHash); }} catch (e) {{ return null; }} }})()}},
    connectedCities: (() => {{ try {{ return city.getConnectedCities().length; }} catch (e) {{ return null; }} }})(),
    constructibleCount: buildings.length,
    constructibles: buildings
  }}, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


GET_VICTORY_PROGRESS_JS = (
    "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
    + _COMMON_FNS + """
  const majors = Players.getAliveMajorIds();
  const teams = {};
  majors.forEach(id => { const t = Players.get(id).team; (teams[t] = teams[t] || []).push(id); });
  const progress = Game.VictoryManager.getVictoryProgress().map(v => {
    const info = GameInfo.Victories.lookup(v.victory);
    return {team: v.team, players: teams[v.team] ?? [],
            victory: info ? info.VictoryType : String(v.victory),
            name: info ? L(info.Name) : null,
            current: v.current, total: v.total};
  });
  const legacy = majors.map(id => {
    const lp = Players.get(id).LegacyPaths;
    let scores = {};
    try {
      [...new Set([...GameInfo.AgeProgressionMilestones].map(m => m.LegacyPathType))].forEach(t => {
        try { scores[t] = lp.getScore(t); } catch (e) { /* skip */ }
      });
    } catch (e) { /* skip */ }
    return {id,
      enabled: (() => { try { return lp.getEnabledLegacyPaths(); } catch (e) { return null; } })(),
      completed: (() => { try { return lp.getCompletedLegacyPaths(); } catch (e) { return null; } })(),
      scores};
  });
  return JSON.stringify({progress, legacyPaths: legacy},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
)


GET_DIPLOMACY_JS = (
    "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
    + _COMMON_FNS + """
  const majors = Players.getAliveMajorIds();
  const pairs = [];
  for (const a of majors) for (const other of majors) {
    if (other <= a) continue;
    const pa = Players.get(a);
    const met = Game.Diplomacy.hasMet(a, other);
    const entry = {a, b: other, met};
    if (met) {
      entry.atWar = pa.Diplomacy.isAtWarWith(other);
      try { entry.relationship = L(pa.Diplomacy.getRelationshipLevelName(other)); } catch (e) { /* skip */ }
      try { entry.relationshipLevel = pa.Diplomacy.getRelationshipLevel(other); } catch (e) { /* skip */ }
      if (entry.atWar) {
        try { const wd = Game.Diplomacy.getWarData(a, other); entry.warName = wd ? L(wd.warName) : null; }
        catch (e) { /* skip */ }
      }
    }
    pairs.push(entry);
  }
  const wars = pairs.filter(p => p.atWar).map(p => ({between: [p.a, p.b], warName: p.warName ?? null}));
  return JSON.stringify({players: majors, activeWars: wars, pairs},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
)


def get_tech_civics_js(player_id: int) -> str:
    """Payload with tech + civic tree state for one player."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const id = {pid};
  if (!Players.isAlive(id)) return JSON.stringify({{error: 'no such alive player: ' + id}});
  const p = Players.get(id);
  const tree = (T) => {{
    if (!T) return null;
    const cur = (() => {{ try {{ return T.getResearching(); }} catch (e) {{ return null; }} }})();
    return {{
      researching: cur && cur.type !== undefined ? {{
        node: lookupName(cur.type), progress: cur.progress,
        turnsLeft: (() => {{ try {{ return T.getTurnsLeft(); }} catch (e) {{ return null; }} }})()
      }} : null,
      researched: (() => {{ try {{ return T.getResearched().map(n => lookupName(n.type)); }} catch (e) {{ return []; }} }})()
    }};
  }};
  return JSON.stringify({{id, civ: L(p.civilizationFullName),
    techs: tree(p.Techs), civics: tree(p.Culture)}},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_units_at_js(x: int, y: int) -> str:
    """Payload with full detail for every unit on a plot."""
    xs, ys = str(int(x)), str(int(y))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const x = {xs}, y = {ys};
  const units = Players.getAliveIds().flatMap(id => {{
    const p = Players.get(id);
    return (p.Units ? p.Units.getUnits() : []).filter(u => u.location.x === x && u.location.y === y)
      .map(u => ({{
        owner: id, name: L(u.name), type: u.typeName,
        isCombat: u.isCombat, isCommander: u.isCommanderUnit, isEmbarked: u.isEmbarked,
        isFortified: u.isFortified, isAutomated: u.isAutomated,
        damage: (() => {{ try {{ return u.Health ? u.Health.damage : null; }} catch (e) {{ return null; }} }})(),
        movesRemaining: (() => {{ try {{ return u.Movement.movementMovesRemaining; }} catch (e) {{ return null; }} }})(),
        maxMoves: (() => {{ try {{ return u.Movement.maxMoves; }} catch (e) {{ return null; }} }})(),
        level: (() => {{ try {{ return u.Experience.getLevel; }} catch (e) {{ return null; }} }})(),
        promotions: (() => {{ try {{ return u.Experience.getPromotions().map(pr => lookupName(pr)); }} catch (e) {{ return null; }} }})(),
        armyId: u.armyId && u.armyId.id !== -1 ? u.armyId.id : null
      }}));
  }});
  return JSON.stringify({{x, y, unitCount: units.length, units}},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_yields_js(player_id: int) -> str:
    """Payload with per-turn net yields for one player or all majors."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const want = {pid};
  const ids = want === -1 ? Players.getAliveMajorIds()
    : (Players.isAlive(want) ? [want] : []);
  if (!ids.length) return JSON.stringify({{error: 'no such alive player: ' + want}});
  const players = ids.map(id => {{
    const p = Players.get(id);
    const net = {{}};
    yieldTypes.forEach(yt => {{
      try {{ net[yt.type] = p.Stats.getNetYield(yt.hash); }} catch (e) {{ /* skip */ }}
    }});
    return {{id, civ: L(p.civilizationFullName),
      goldBalance: p.Treasury ? Math.round(p.Treasury.goldBalance) : null,
      netYieldsPerTurn: net}};
  }});
  return JSON.stringify(want === -1 ? {{players}} : players[0],
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_city_production_js(player_id: int) -> str:
    """Payload with every city's production queue for one player / all majors."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const want = {pid};
  const ids = want === -1 ? Players.getAliveMajorIds()
    : (Players.isAlive(want) ? [want] : []);
  if (!ids.length) return JSON.stringify({{error: 'no such alive player: ' + want}});
  const players = ids.map(id => {{
    const p = Players.get(id);
    const cities = (p.Cities ? p.Cities.getCities() : []).map(c => {{
      const bq = c.BuildQueue;
      return {{
        city: L(c.name), x: c.location.x, y: c.location.y, isTown: c.isTown,
        producing: bq.isEmpty ? null : lookupName(bq.currentProductionTypeHash),
        turnsLeft: bq.isEmpty ? null : bq.currentTurnsLeft,
        queue: (() => {{ try {{ return bq.getQueue().map(q =>
          lookupName(q.constructibleType !== -1 ? q.constructibleType
                     : (q.unitType !== -1 ? q.unitType : q.projectType))); }} catch (e) {{ return []; }} }})()
      }};
    }});
    return {{id, civ: L(p.civilizationFullName), cities}};
  }});
  return JSON.stringify(want === -1 ? {{players}} : players[0],
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


GET_WONDERS_JS = (
    "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
    + _COMMON_FNS + """
  const built = [];
  Players.getAliveIds().forEach(id => {
    const p = Players.get(id);
    (p.Cities ? p.Cities.getCities() : []).forEach(c => {
      try {
        c.Constructibles.getIds().forEach(cid => {
          const inst = Constructibles.get(cid);
          if (!inst) return;
          const info = GameInfo.Constructibles.lookup(inst.type);
          if (info && info.ConstructibleClass === 'WONDER')
            built.push({wonder: info.ConstructibleType, name: L(info.Name),
              city: L(c.name), owner: id, x: inst.location.x, y: inst.location.y,
              complete: inst.complete});
        });
      } catch (e) { /* skip city */ }
    });
  });
  const natural = [];
  const w = GameplayMap.getGridWidth(), h = GameplayMap.getGridHeight();
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (!GameplayMap.isNaturalWonder(x, y)) continue;
    const f = GameplayMap.getFeatureType(x, y);
    const info = f !== -1 ? GameInfo.Features.lookup(f) : null;
    const type = info ? info.FeatureType : String(f);
    let entry = natural.find(n => n.type === type);
    if (!entry) natural.push(entry = {type, name: info ? L(info.Name) : null, tiles: []});
    entry.tiles.push({x, y});
  }
  return JSON.stringify({builtWonders: built, naturalWonders: natural},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
)


GET_RELIGION_JS = (
    "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
    + _COMMON_FNS + """
  const players = Players.getAliveMajorIds().map(id => {
    const R = Players.get(id).Religion;
    if (!R) return {id, error: 'no Religion object'};
    const g = (fn, ...args) => { try { return fn.apply(R, args); } catch (e) { return null; } };
    return {id, civ: L(Players.get(id).civilizationFullName),
      hasPantheon: g(R.hasPantheon),
      pantheons: (() => { try { return R.getPantheons().map(b => {
        const info = GameInfo.Beliefs ? GameInfo.Beliefs.lookup(b) : null;
        return info ? info.BeliefType : String(b); }); } catch (e) { return null; } })(),
      hasCreatedReligion: g(R.hasCreatedReligion),
      religionName: (() => { try { return L(R.getReligionName()) || null; } catch (e) { return null; } })(),
      beliefs: (() => { try { return R.getBeliefs().map(b => {
        const info = GameInfo.Beliefs ? GameInfo.Beliefs.lookup(b) : null;
        return info ? info.BeliefType : String(b); }); } catch (e) { return null; } })(),
      hasHolyCity: g(R.hasHolyCity),
      holyCity: (() => { try { return L(R.getHolyCityName()) || null; } catch (e) { return null; } })(),
      majorityReligionInCities: g(R.getReligionInMajorityOfCities)};
  });
  return JSON.stringify({players},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
)


def get_trade_routes_js(player_id: int) -> str:
    """Payload listing active trade routes for one player / all majors."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const want = {pid};
  const ids = want === -1 ? Players.getAliveMajorIds()
    : (Players.isAlive(want) ? [want] : []);
  if (!ids.length) return JSON.stringify({{error: 'no such alive player: ' + want}});
  const cityName = (cid) => {{
    try {{ const c = Cities.get(cid); return c ? L(c.name) : null; }} catch (e) {{ return null; }}
  }};
  const players = ids.map(id => {{
    const p = Players.get(id);
    const routes = (() => {{ try {{ return p.Trade.getCurrentTradeRoutes(); }} catch (e) {{ return []; }} }})();
    return {{id, civ: L(p.civilizationFullName), routeCount: routes.length,
      routes: routes.map(r => ({{
        from: cityName(r.nearestCityId), fromOwner: r.nearestCityId ? r.nearestCityId.owner : null,
        to: cityName(r.targetCityId), toOwner: r.targetCityId ? r.targetCityId.owner : null,
        domain: r.domain,
        imports: (r.importPayloads || []).map(e => {{
          const info = GameInfo.Resources.lookup(e.uniqueResource ? e.uniqueResource.resource : e);
          return info ? info.ResourceType : 'unknown';
        }}),
        exportYields: (r.exportYields || []).map(e => {{
          const info = GameInfo.Yields.lookup(e.yieldType);
          return {{yield: info ? info.YieldType : String(e.yieldType), amount: e.amount}};
        }})
      }}))}};
  }});
  return JSON.stringify(want === -1 ? {{players}} : players[0],
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_notifications_js(player_id: int) -> str:
    """Payload listing pending notifications / turn blockers for a player."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const id = {pid};
  const N = Game.Notifications;
  const ids = (() => {{ try {{ return N.getIdsForPlayer(id) || []; }} catch (e) {{ return []; }} }})();
  const notifications = ids.map(nid => ({{
    type: (() => {{ try {{ return N.getTypeName(nid); }} catch (e) {{ return null; }} }})(),
    message: (() => {{ try {{ return L(N.getMessage(nid)); }} catch (e) {{ return null; }} }})(),
    summary: (() => {{ try {{ return L(N.getSummary(nid)); }} catch (e) {{ return null; }} }})(),
    severity: (() => {{ try {{ return N.getSeverity(nid); }} catch (e) {{ return null; }} }})(),
    blocksTurn: (() => {{ try {{ return N.getBlocksTurnAdvancement(nid); }} catch (e) {{ return null; }} }})()
  }}));
  return JSON.stringify({{player: id, count: notifications.length,
    hasEndTurnBlocking: (() => {{ try {{ return N.hasEndTurnBlocking(id); }} catch (e) {{ return null; }} }})(),
    notifications}},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def get_milestones_js(player_id: int) -> str:
    """Payload with age-progression milestones + per-player legacy scores."""
    pid = str(int(player_id))
    return (
        "(() => {\n  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});\n"
        + _COMMON_FNS + f"""
  const want = {pid};
  const ids = want === -1 ? Players.getAliveMajorIds()
    : (Players.isAlive(want) ? [want] : []);
  if (!ids.length) return JSON.stringify({{error: 'no such alive player: ' + want}});
  const milestones = [...GameInfo.AgeProgressionMilestones].map(m => ({{
    milestone: m.AgeProgressionMilestoneType,
    legacyPath: m.LegacyPathType,
    requiredPoints: m.RequiredPathPoints,
    final: m.FinalMilestone,
    complete: (() => {{ try {{ return Game.AgeProgressManager.isMilestoneComplete(m.$hash); }} catch (e) {{ return null; }} }})()
  }}));
  const paths = [...new Set(milestones.map(m => m.legacyPath))];
  const players = ids.map(id => {{
    const lp = Players.get(id).LegacyPaths;
    const scores = {{}};
    paths.forEach(t => {{ try {{ scores[t] = lp.getScore(t); }} catch (e) {{ /* skip */ }} }});
    return {{id, civ: L(Players.get(id).civilizationFullName),
      completedPaths: (() => {{ try {{ return lp.getCompletedLegacyPaths(); }} catch (e) {{ return null; }} }})(),
      scores}};
  }});
  return JSON.stringify({{milestones, players}},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
}})()"""
    )


def search_api_js(object_expr: str, pattern: str) -> str:
    """Payload walking an object's prototype chain for members matching a regex."""
    obj = json.dumps(object_expr)
    pat = json.dumps(pattern)
    return (
        """(() => {
  let target;
  try { target = eval(""" + obj + """); }
  catch (e) { return JSON.stringify({error: 'eval failed: ' + e}); }
  if (target === null || target === undefined)
    return JSON.stringify({error: 'expression is ' + String(target)});
  let re;
  try { re = new RegExp(""" + pat + """, 'i'); }
  catch (e) { return JSON.stringify({error: 'bad regex: ' + e}); }
  const members = [];
  const seen = new Set();
  let proto = target, depth = 0;
  while (proto && proto !== Object.prototype && depth < 8) {
    for (const n of Object.getOwnPropertyNames(proto)) {
      if (seen.has(n) || !re.test(n)) continue;
      seen.add(n);
      let kind = 'property', arity = null, value;
      try {
        const v = target[n];
        if (typeof v === 'function') { kind = 'function'; arity = v.length; }
        else if (typeof v !== 'object') value = String(v).slice(0, 60);
      } catch (e) { kind = 'getter (threw)'; }
      const m = {name: n, kind};
      if (arity !== null) m.arity = arity;
      if (value !== undefined) m.value = value;
      members.push(m);
    }
    proto = Object.getPrototypeOf(proto);
    depth++;
  }
  return JSON.stringify({object: """ + obj + """, pattern: """ + pat + """,
    matchCount: members.length, members: members.slice(0, 120)},
    (k, v) => typeof v === 'bigint' ? v.toString() : v, 1);
})()"""
    )


def autoplay_js(action: str, turns: int, observe_as: int) -> str:
    """Payload starting/stopping FireTuner-style autoplay (verified recipe)."""
    if action == "stop":
        return """(() => {
  Autoplay.setActive(false);
  return JSON.stringify({autoplay: 'stopped', turn: Game.turn});
})()"""
    t, obs = str(int(turns)), str(int(observe_as))
    return (
        """(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  Autoplay.setTurns(""" + t + """);
  Autoplay.setReturnAsPlayer(""" + obs + """);
  Autoplay.setObserveAsPlayer(""" + obs + """);
  Autoplay.setActive(true);
  return JSON.stringify({autoplay: 'started', turns: """ + t + """,
    observeAs: """ + obs + """, startTurn: Game.turn});
})()"""
    )


END_TURN_JS = """
(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  const before = Game.turn;
  GameContext.sendTurnComplete();
  return JSON.stringify({sent: true, turnWhenSent: before,
    note: 'turn advances asynchronously; re-check Game.turn (blocked by unmoved units/choices - see get_notifications)'});
})()
"""


def look_at_js(x: int, y: int) -> str:
    """Payload pointing the camera at a plot (pairs with screenshot)."""
    xs, ys = str(int(x)), str(int(y))
    return (
        """(() => {
  if (!UI.isInGame()) return JSON.stringify({error: 'not in a game'});
  Camera.lookAtPlot(""" + xs + """, """ + ys + """);
  return JSON.stringify({lookingAt: {x: """ + xs + """, y: """ + ys + """}});
})()"""
    )


RELOAD_UI_JS = """
(() => {
  UI.reloadUI();
  return JSON.stringify({reloading: true,
    note: 'UI documents + JS/CSS re-fetched; database/module-cache changes still need a game restart'});
})()
"""


def preflight_mod_js_start(module_path: str) -> str:
    """Kick off a cache-busted dynamic import; result read by _POLL below."""
    mod = json.dumps(module_path)
    return (
        """(() => {
  globalThis.__c7_preflight = {done: false};
  import(""" + mod + """ + '?v=' + Date.now())
    .then(m => { globalThis.__c7_preflight = {done: true, ok: true,
      exports: Object.keys(m).slice(0, 40)}; })
    .catch(e => { globalThis.__c7_preflight = {done: true, ok: false,
      error: String(e && e.message || e)}; });
  return JSON.stringify({started: true});
})()"""
    )


PREFLIGHT_MOD_POLL_JS = "JSON.stringify(globalThis.__c7_preflight || {done: false})"


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
