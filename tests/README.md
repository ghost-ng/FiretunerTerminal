# Automated Game Testing & Debugging via the MCP Server

This folder documents how to use the FireTuner Terminal MCP server to drive
**automated, agent-run tests** against a live Civilization VII instance —
Playwright-style: configure a game through real APIs, press UI buttons,
launch, wait, assert on game state, and diagnose failures from logs.

Everything here was proven live against the game (2026-08-16) while testing
the Continents++ map mod, including a full failure-diagnosis cycle after a
game patch broke the mod's imports.

## Documents

| File | Contents |
|------|----------|
| [mcp-testing.md](mcp-testing.md) | MCP server specifics for automation: tool behavior, result quirks, contexts, module cache-busting |
| [game-api-testing.md](game-api-testing.md) | Game APIs for test setup & assertions: `GameSetup`, `Configuration`, `GameplayMap`, `Players`, verification patterns |
| [ui-automation.md](ui-automation.md) | Driving the shell UI: DOM querying, the `engine-input` button-press pattern, screens, dialogs |
| [debugging.md](debugging.md) | Failure diagnosis: log files, the dynamic-import preflight, what needs a restart vs a reload vs nothing |

## API discovery & exploration

Companion material for finding and validating the APIs the tests above rely on:

| File | Contents |
|------|----------|
| [probe.py](probe.py) | Minimal synchronous debug-port client: `python tests/probe.py '<js>'` sends one expression and prints the response; import `Probe` for scripted sessions |
| [api-crawling.md](api-crawling.md) | How to discover/validate API functions and calls: static source-map crawl vs live prototype-chain introspection, grep pitfalls, batch probing, validation rules |
| [pause-menu-exit-to-menu.md](pause-menu-exit-to-menu.md) | Worked example: enumerate the pause menu options live and return to the main menu via `engine.call("exitToMainMenu")` |

## The test loop at a glance

```
┌─ 0. PREFLIGHT ── dynamic-import the mod's script → catches broken
│                  imports in seconds (game logs won't tell you)
├─ 1. CONFIGURE ── GameSetup.setGameParameterValue(...) → verify via
│                  Configuration.getMap().getValue(...)
├─ 2. LAUNCH ───── engine-input presses: NEW GAME → Select → Continue
│                  → Launch Game
├─ 3. AWAIT ────── poll { UI.isInGame(), error dialog?, screen stack }
├─ 4a. PASS ────── run an assertion payload (single IIFE returning
│                  JSON.stringify'd {checks, stats, passed})
└─ 4b. FAIL ────── Scripting.log tail → preflight import → persisted
                   mod logs → dismiss dialog → fix → redeploy → relaunch
                   (map scripts reload per launch, NO game restart needed)
```

## Ground rules for agent-driven tests

1. **Always `JSON.stringify` the last expression.** Bare numbers/objects come
   back empty or as `[object Object]` through the tuner protocol.
2. **One self-contained IIFE per assertion payload.** State does persist on
   `globalThis` between calls (same context), but a test should not depend
   on leftovers from previous calls — except for the async-result pattern
   (see mcp-testing.md).
3. **Prefer real APIs over UI clicks** for configuration (`GameSetup`), and
   UI clicks only for flow transitions that have no API (launching, dialogs).
4. **Verify every write.** A failed launch silently resets all setup
   parameters to defaults — read back the config before pressing Launch.
5. **Structure results as pass/fail checks**, not prose:
   `{checks: [{name, pass, detail}], stats: {...}, passed: bool}` — so a
   harness (or an agent) can gate on `passed` and diff `stats` across runs.

## Example: a complete test spec

See the Continents++ repo for a worked example:

- `ContinentsPlusPlus/research/testing-workflow.md` — full test definition
  (T01), phase-by-phase evaluation methodology, and a real postmortem
- `ContinentsPlusPlus/scripts/mapgen-test-suite.js` — an assertion payload
  that scans every map tile and checks per-player invariants
