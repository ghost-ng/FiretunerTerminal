# Game APIs for Test Automation

The API surface used to configure, launch, and assert on games. All verified
live. General gameplay APIs are in the repo's `API_LIBRARY.md`; this file
covers the automation-relevant subset and patterns.

## GameSetup — configuring a game (shell context)

The programmatic equivalent of the entire game-creation UI. Works only in
the shell (main menu / create-game flow).

```js
// Read any setup parameter (base game or mod-defined)
const p = GameSetup.findGameParameter('MapSize');
p.value.value;                          // current value, e.g. "MAPSIZE_STANDARD"
GameSetup.resolveString(p.value.name);  // display string (resolves LOC_ keys)
p.domain.possibleValues;                // [{value, name, description, icon, ...}]
p.readOnly;                             // whether UI would allow changing it

// Write
GameSetup.setGameParameterValue(p.ID, 'MAPSIZE_STANDARD');
```

Known parameter IDs: `Map`, `MapSize`, `Age`, `Difficulty`, `GameSpeeds`,
`AgeTransitionSetting`, plus any mod-registered `Parameters` rows (e.g.
`ContinentsPPContinentCount`). Player-scoped variants exist via
`GameSetup.findPlayerParameter(playerId, id)`.

Setting `Map` re-registers map-specific parameters; setting `MapSize`
auto-adjusts the participating player count to the size default.

**Verify writes through Configuration** (this is what map scripts read):

```js
Configuration.getMap().getValue('SomeConfigurationKey')
```

**Pitfall**: a failed map generation bounces back to the main menu and
RESETS all setup parameters to defaults. Re-apply and re-verify before
relaunching.

## Configuration — cross-context data bus

- `Configuration.getMap().getValue(key)` / `Configuration.getGame()` —
  readable from every context.
- `Configuration.editMap().setValue(key, value)` — writable during map
  generation; this is how a map script exports data (versions, logs, debug
  stats) for later assertion from the UI context.
- Roster info: `Configuration.getGame().getParticipatingPlayerCount()`,
  `.participatingPlayerIDs`, `.aiPlayerCount`, `.humanPlayerCount`,
  `.maxJoinablePlayerCount`.

Pattern — a mod persisting its logs for tests (from Continents++):

```js
// In the map script (MapGeneration context):
Configuration.editMap().setValue("MyModLogs", JSON.stringify(logLines));
// In a test (UI context, after load):
JSON.parse(Configuration.getMap().getValue("MyModLogs") || "[]")
```

## GameplayMap — map-state assertions (in game)

```js
GameplayMap.getGridWidth() / getGridHeight()
GameplayMap.getContinentType(x, y)      // -1 = water, else continent ID
GameplayMap.getLandmassRegionId(x, y)   // 2 = WEST/homeland, 1 = EAST/distant
GameplayMap.getContinentName(x, y)
GameplayMap.getRandomSeed()
```

A full-map scan (Standard 84×54 ≈ 4.5k tiles) inside one payload is fast
and reliable — collect Sets/Maps, return one JSON report.

### Terrain / resource scan patterns (verified)

```js
// There is NO GameplayMap.isCoastalWater. Terrain classes come from rows:
const row = GameInfo.Terrains.lookup(GameplayMap.getTerrainType(x, y));
row.TerrainType   // 'TERRAIN_COAST' | 'TERRAIN_OCEAN' | 'TERRAIN_FLAT' | ...

GameplayMap.isMountain(x, y)        // exists
GameplayMap.isCoastalLand(x, y)     // exists (land adjacent to water)
GameplayMap.getPlotDistance(x1, y1, x2, y2)  // hex distance — spawn spacing

// Resources: getResourceType → -1/null for none, else GameInfo lookup
const rt = GameplayMap.getResourceType(x, y);
if (rt != null && rt !== -1) {
  const res = GameInfo.Resources.lookup(rt);  // .ResourceType e.g. 'RESOURCE_GOLD'
}
```

Useful assertions built from these: resource density and variety, resources
present on distant-lands tiles (region 0) for treasure mechanics, mountain
and coast counts, distinct `getContinentType` values ≥ 2.

## Players — per-player assertions (in game)

```js
Players.getAliveMajorIds()              // [0..n]
Players.isHuman(id) / Players.isAI(id)
const p = Players.get(id);
p.Cities.getCapital()?.location         // {x, y} once founded
p.Units.getUnits()[0]?.location         // spawn location pre-settle
p.isDistantLands({x, y})                // per-player homeland perspective
```

### Stamped continents vs. physical landmasses (important distinction)

`GameplayMap.getContinentType(x, y)` returns the engine's **named continent**
stamp — and `TerrainBuilder.stampContinents()` groups nearby separate
landmasses and their islands into one named continent. A map with 6
ocean-separated landmasses can legitimately report only 4 stamped
continents, each spanning multiple landmass region IDs. So:

- To assert "N continents were generated" → count **connected land
  components** (flood fill over `getContinentType(x,y) !== -1`), not
  distinct continent IDs.
- Stamped continent count is a naming/cosmetic metric; landmass region IDs
  drive gameplay (homelands, distant lands).

Connected-component counter (hex grid, odd-row offset, X-wrap):

```js
const seen = new Set(); const sizes = [];
const isLand = (x, y) => GameplayMap.getContinentType(x, y) !== -1;
for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
  if (!isLand(x, y) || seen.has(x + ',' + y)) continue;
  let size = 0; const q = [{x, y}]; seen.add(x + ',' + y);
  while (q.length) {
    const cur = q.pop(); size++;
    const odd = cur.y & 1;
    for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1],[odd?1:-1,1],[odd?1:-1,-1]]) {
      let nx = cur.x + dx; const ny = cur.y + dy;
      if (nx < 0) nx = w - 1; if (nx >= w) nx = 0;      // X-wrap
      if (ny < 0 || ny >= h) continue;
      const nk = nx + ',' + ny;
      if (!seen.has(nk) && isLand(nx, ny)) { seen.add(nk); q.push({x: nx, y: ny}); }
    }
  }
  sizes.push(size);
}
// sizes.filter(s => s >= 40).length ≈ major landmasses; the rest are islands
```

This proved a map-tuning question in one query: 6 rolled landmasses →
6 physical components of ~200-240 tiles each, despite only 4 stamped
continents.

### Distribution tuning via the test loop (pattern)

Map-parameter tuning is measurable per run: generate → scan → adjust →
regenerate (~90 s/cycle, no game restart for map-script changes). Metrics
that proved useful: water % (land/(land+water)), distant-land share
(region-0 land / land), physical landmass count vs rolled config, per-size
comparisons (Tiny vs Huge budgets need independent scaling).

### Per-player homeland verification (verified)

`player.isDistantLands({x, y})` is relative to the player's spawn region
(landmass region id). With multiple player landmass groups, two players in
different groups each see the other's homeland as Distant Lands —
symmetrically. Test pattern:

```js
// human in region A, ai in region B (A != B, both > 0):
Players.get(ai.id).isDistantLands({x: human.x, y: human.y})   // → true
Players.get(human.id).isDistantLands({x: ai.x, y: ai.y})      // → true
// and each player's own spawn:
Players.get(id).isDistantLands(ownSpawn)                       // → false
```

Region id 0 (islands + dedicated distant landmasses) is distant to everyone.

## UI / engine — meta controls

```js
UI.isInGame()               // false in shell, true once loaded
UI.reloadUI()               // reload UI documents from VFS (drops to main menu)
engine.reloadLocalization() // re-sync localization
```

## Assertion payload shape

Return machine-checkable reports, one IIFE per payload:

```js
(() => {
  const report = { checks: [], stats: {}, failures: 0 };
  const check = (name, pass, detail) => {
    report.checks.push({ name, pass: !!pass, detail });
    if (!pass) report.failures++;
  };
  if (!UI.isInGame()) return JSON.stringify({ ready: false });

  check("example: grid loaded", GameplayMap.getGridWidth() > 0, "");
  // ... more checks ...

  report.passed = report.failures === 0;
  return JSON.stringify(report);
})()
```

Worked example: `ContinentsPlusPlus/scripts/mapgen-test-suite.js` — asserts
mod log lines, binary region IDs across all tiles, one-region-per-continent,
water percentage bounds, and per-player `isDistantLands` correctness.
