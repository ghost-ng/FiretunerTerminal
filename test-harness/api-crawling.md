# How to Crawl the Civ7 JavaScript API

Methodology for discovering, enumerating, and validating API functions and
calls. Two complementary approaches exist; use both, because each one misses
things the other catches.

| | Static crawl (game files) | Live crawl (debug port) |
|---|---|---|
| What it finds | Call sites the game's own UI code uses | Everything the engine actually exposes |
| Misses | Engine APIs no game JS calls (`UI.debugPrint`, `WorldBuilder.startBlock`, `GameplayMap.getYield`) | Nothing, but needs the right context loaded |
| Needs game running | No | Yes (and a loaded save for gameplay objects) |
| Authority | Weak — absence proves nothing | **Authoritative** |

## 1. Static crawl of the game files

Game dir: `C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VII`

- **Prefer `.js.map` source maps** over `.js`: their `sourcesContent` field
  holds the original TypeScript, which carries type annotations
  (`const x: PlayerId = ...`) that raw JS lost.
- The automated pipeline is `python -m civ7_terminal.extract_types` → writes
  `completions.json` (drives Tab completion; `TYPE_REFERENCE.md` is generated
  from it).
- For one-off searches, grep the `.js` files directly.

### Grep correctly — the receiver-suffix trap

A naive `grep 'UI\.createModelGroup'` matches the **tail** of
`WorldUI.createModelGroup` and produces false positives (this exact bug put
~100 wrong entries in an early `completions.json`). Always anchor the
receiver with a lookbehind:

```bash
grep -rhoP "(?<![.\w])UI\.createModelGroup" "$GAME_DIR" --include="*.js"
```

Same idea in Python: `re.compile(r'(?<![.\w])' + re.escape(name) + r'\.(\w+)\s*\(')`.

### Interpreting static results

- **Found**: the API exists and this is how the game itself calls it —
  copy the call shape (arg count, arg sources) from the surrounding code.
- **Not found**: means only "no game JS calls it". It may still exist
  engine-side. Never delete a documented API on static absence alone —
  verify live first.
- Three receiver shapes matter: bare globals (`GameplayMap.foo()`),
  sub-objects (`player.Cities.foo()`, `Game.Diplomacy.foo()` — match
  `\w+\.Cities\.` since the variable name varies), and instance methods
  (`city.foo()` — the receiver is an arbitrary variable, so match on the
  method name only and confirm the owner live).

## 2. Live crawl over the debug port

Send JS with `python test-harness/probe.py '<expr>'`. The **last expression is the
return value**; wrap complex output in `JSON.stringify(...)`.

### Know your context

The debug port serves whatever UI context is loaded:

```js
UI.isInShell()   // true at main menu — only Configuration, UI, GameContext, engine, Locale, ...
UI.isInGame()    // true with a save loaded — GameplayMap, Players, Game, ... exist
```

At the main menu, `typeof GameplayMap` is `"undefined"`. That is not an API
removal — load a game and re-check.

### Enumerate an object's members (the core recipe)

Engine objects keep their methods on the **prototype chain**, so
`Object.keys(obj)` returns almost nothing. Walk the chain:

```js
(function(){
  var names = new Set(); var o = GameplayMap;
  while (o && o !== Object.prototype) {
    Object.getOwnPropertyNames(o).forEach(function(n){ names.add(n); });
    o = Object.getPrototypeOf(o);
  }
  return JSON.stringify(Array.from(names).sort());
})()
```

Works for any receiver: swap in `Players.get(GameContext.localPlayerID)`,
`...Cities.getCapital()`, `Configuration.getGame()`, etc.

### Batch-probe a list of candidates

One round-trip per object, not per method:

```js
(function(){
  var o = Game.Diplomacy, out = {};
  ["hasMet","getVictories","getWarData"].forEach(function(n){ out[n] = typeof o[n]; });
  return JSON.stringify(out);
})()
```

`"function"` = method, `"number"/"string"/"object"/"boolean"` = property,
`"undefined"` = not on this receiver (try siblings before concluding it's
gone — `getVictories` lives on `Game.VictoryManager`, not `Game.Diplomacy`).

### Discover sub-objects

Instance dumps reveal capitalized sub-object members (a city exposes
`Growth`, `Production`, `Yields`, `Districts`, `Constructibles`, ...). Recurse
the member-enumeration recipe into each to map the full tree.

### Find the write/action APIs

Action-style calls often go through `engine.call("name", ...)` rather than a
typed global. Crawl candidates statically:

```bash
grep -rhoP 'engine\.call\("(\w+)"' "$GAME_DIR" --include="*.js" | sort -u
```

Handlers in `ui/.../screens/*/**-model.js` files show which engine calls each
button ultimately makes (see `test-harness/pause-menu-exit-to-menu.md` for a worked
example).

## 3. Validation workflow (what to trust)

1. Static crawl proposes; **live probe disposes.** Only a live `"undefined"`
   on the correct receiver, in the correct context (in-game vs menu), proves
   an API is gone.
2. When the game updates: re-run `extract_types`, diff `completions.json`,
   then live-verify every *removal* before believing it — additions are safe,
   removals are usually just usage churn in the game's own code.
3. Instrument nothing you can't undo: probes with `typeof` and
   `getOwnPropertyNames` are read-only and safe; calling unknown methods is
   not (some mutate game state — `changeGoldBalance`, `forceDeclareWar`).
   Probe existence first, call deliberately.
4. Expect the socket to drop on context transitions (loading a save, exiting
   to menu, `UI.reloadUI()`); reconnect and re-check context before resuming.
5. Feed confirmed discoveries back into `API_LIBRARY.md` (curated reference)
   and let `completions.json` stay purely machine-generated.
