# MCP Server Specifics for Test Automation

Behavior of the `civ7` MCP server (`execute_js` over the FireTuner protocol,
TCP 4318) that matters when writing automated tests.

## Result semantics

- The **last expression** of the payload is the returned result, as a string.
- **Bare numbers and objects often return `""` or `[object Object]`** —
  always end payloads with `JSON.stringify(...)`. Even `1+1` can come back
  empty; `JSON.stringify(1+1)` does not.
- Exceptions inside the payload surface as error text — but wrapping the
  whole payload in an IIFE with explicit returns gives far cleaner results.

## Execution context

- Commands run in the game's **UI JavaScript context** (cohtml). Available:
  `document`, `window`, `GameSetup`, `Configuration`, `UI`, `engine`,
  `GameplayMap`, `Players`, `InputActionStatuses`, dynamic `import()`.
- The context follows the game: at the main menu you get the shell document
  (`UI.isInGame() === false`); in a loaded game you get gameplay state.
- **Map generation runs in a separate, short-lived context**
  (`MapGeneration` in Scripting.log). You can NEVER attach to it live — it
  is created at launch and destroyed when generation ends. To see inside
  it: `console.log` from the script (lands in `Scripting.log`), or persist
  values via `Configuration.editMap().setValue(...)` and read them later
  from the UI context.

## State between calls

`globalThis` persists between `execute_js` calls (same context lifetime).
This enables the **async-result pattern** — the only way to get results from
promises, since the tool returns synchronously:

```js
// call 1: kick off
globalThis.__result = 'pending';
somePromise().then(r => { globalThis.__result = 'OK: ' + r; })
             .catch(e => { globalThis.__result = 'ERR: ' + e.message; });
'kicked'
```
```js
// call 2: collect
globalThis.__result
```

Context resets (UI.reloadUI, entering/leaving a game) wipe `globalThis`.

## Module cache-busting

`import('fs://game/<modid>/path/file.js')` caches by URL — after redeploying
a changed file, re-importing the same URL returns the OLD module (or its
cached failure). Append a throwaway query to force a fresh load:

```js
import('fs://game/<modid>/path/file.js?v=' + Date.now())
```

This is the backbone of the **preflight import check** (see debugging.md):
it validates a mod script's entire import graph in seconds without a launch.

**Caveat**: mod-file imports (`fs://game/<modid>/...`) only work from the
main menu / shell. During an active game session they hang forever (promise
never settles) — base-game module imports still work. Preflight at the menu.

## Cross-context persistence (map-gen → tests)

The map-gen context is destroyed after generation; to hand data to a later
test, persist it. The API differs by engine version — write with fallbacks:

```js
// In the map script:
try { Configuration.editMap().setValue(key, json); }        // old engine
catch (e) { try { Game.setProperty(key, json); } catch (e2) {} }  // new engine
// In the test (in-game context):
Configuration.getMap().getValue(key) ?? Game.getProperty(key)
```

## Timing & polling

- There is no sleep/wait primitive — poll by issuing repeated small
  `execute_js` calls (`UI.isInGame()`, dialog presence, screen stack).
- Loading screens keep the debug port responsive; polling during a game
  launch is safe.
- After `UI.reloadUI()` expect a brief window where queries return
  empty/partial DOM.

## Multiplayer / hotseat limitation (verified 2026-08-16)

**The game CLOSES the FireTuner port (4318) in multiplayer contexts —
including local hotseat.** Sequence observed: main menu → MULTIPLAYER →
hotseat → game creator all respond normally (GameSetup writes verified);
the moment "Host Lobby" opens the staging screen, commands time out, and
shortly after the listener is gone entirely — new connections get
ConnectionRefused while the game runs fine. Anti-cheat behavior. The MCP
server will show as disconnected; it recovers when the port reopens (after
leaving the MP session — verify timing when known).

Consequences for automation:
- Hotseat lobby setup (adding human slots, launching) cannot be driven via
  MCP — manual step.
- **The tuner does NOT revive once the hotseat game loads** (verified
  2026-08-16: Turn 1 in a loaded hotseat game, port 4318 has no listener
  at all — the game process listens only on 9444).
- Fallback verification channel: the map script's `console.log` output in
  `Scripting.log` (map-gen context logging is unaffected), plus any state
  the script persists via `Game.setProperty`.

### Workaround: Cohtml UI remote debugger (verified 2026-08-16, in hotseat)

With `UIDebugger 1` in AppOptions.txt, the game serves the Chrome DevTools
Protocol on **port 9444** (Coherent Gameface), and this listener stays up
in multiplayer/hotseat while the tuner is suspended. `Runtime.evaluate`
executes JS in the UI context (`fs://game/root-game.html`) — same context
the tuner's CMD channel uses, so `Game`, `Players`, `GameplayMap`, DOM,
and `engine` are all reachable:

    # discover the page target
    curl http://127.0.0.1:9444/json
    # then over ws://127.0.0.1:9444/json/devtools/page/0 :
    {"id":1,"method":"Runtime.evaluate",
     "params":{"expression":"Game.turn","returnByValue":true}}

Verified live in a hotseat game: `1+1` → 2, `Game.turn` → 1,
`Players.getAliveMajorIds()` → [0..5]. Python: `websocket-client` package,
`create_connection('ws://127.0.0.1:9444/json/devtools/page/0')`.

Caveats: only one CDP client at a time (the official Dev Tools app competes
for it); JSON-RPC framing instead of the tuner protocol, so the MCP server
does not use it (yet); local debugging only — do not use to interact with
real online multiplayer sessions.

Hotseat entry (the part that DOES automate): the MP landing/creator screens
are old-framework — plain `action-activate` CustomEvent dispatch works
(`.mp-landing-new__hotseat-button`, then `fxs-hero-button` with caption
`LOC_UI_MP_HOST_LOBBY`).

## Connection notes

- If the game is not running, calls fail at the transport level — treat as
  "game down", not as a test failure.
- `civ7://status` resource reports connection state; `civ7://api-library`
  serves the full API reference (repo file `API_LIBRARY.md`).
