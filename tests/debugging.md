# Debugging Failed Tests

Diagnosis workflow for when a launch fails or an assertion payload reports
failures. Ordered by information value.

## 1. The dynamic-import preflight (fastest, most precise)

The game's own logs hide module errors behind `Uncaught hole undefined:0` /
"Script module failed to instantiate". Dynamic import in the live UI context
surfaces the REAL error with a message:

```js
// call 1
globalThis.__t = 'pending';
import('fs://game/<ModId>/path/script.js?v=' + Date.now())
  .then(m => { globalThis.__t = 'OK: ' + Object.keys(m).join(','); })
  .catch(e => { globalThis.__t = 'ERR: ' + e.message; });
'kicked'
// call 2
globalThis.__t
```

Real example (game patch moved base-game exports):

```
ERR: SyntaxError: The requested module '/base-standard/scripts/kd-tree.js'
     does not provide an export named 'TerrainType'
```

`OK` means the entire import graph resolves AND top-level code evaluated.
Caveats: the `?v=` cache-buster is mandatory after redeploys; top-level code
runs in the UI context (harmless for well-behaved scripts that guard their
engine calls).

## 2. Log files

`%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VII\Logs\`

| File | What's in it |
|------|--------------|
| `Scripting.log` | **The map-gen script engine.** Every `console.log` from map scripts, context lifecycle (`Creating Context - MapGeneration`), and module load failures. The LAST mod log line before `Destroying Context - MapGeneration` pinpoints where generation died — runtime errors usually are NOT printed; the log just stops. |
| `Database.log` | XML load errors (wrong columns, wrong scope, "no such table") |
| `Modding.log` | Mod discovery/activation, action group application |
| `UI.log` | Shell UI errors — decorator scripts, cohtml issues |
| `GameCore.log` | Engine-level game state |

The logs directory is recreated per game session; timestamps distinguish
runs within a session.

## 3. Mod-persisted state (if generation got far enough)

A mod can persist diagnostics via `Configuration.editMap().setValue(...)`
during generation, readable from any later context:

```js
Configuration.getMap().getValue('ContinentsPlusPlusVersion')
JSON.parse(Configuration.getMap().getValue('ContinentsPlusPlusLogs') || '[]').join('\n')
```

## 4. UI state

Where did the flow land? (dialog text, screen stack, buttons — see
ui-automation.md). The fatal-error dialog text is generic ("Map generation
script had a fatal error"); the substance is always in Scripting.log or the
preflight.

## What requires a restart vs. not

| Changed | Pickup mechanism |
|---------|------------------|
| Map/gameplay script (`.js` under a `<ScriptModules>` module) | **Nothing** — the MapGeneration context is created per launch and reads the deployed file from disk. Fix → deploy → relaunch. |
| Shell UI scripts / CSS (`<UIScripts>`) | `UI.reloadUI()` (drops to main menu) |
| Localized text | `engine.reloadLocalization()` (partially verified) |
| XML database (config, parameters, icons), `.modinfo` actions, `<ImportFiles>` | **Full game restart** — databases and the mod file manifest are built at boot |

## Known V8/engine error translations

| Symptom | Actual meaning |
|---------|----------------|
| `Uncaught hole undefined:0` + "Script module failed to instantiate" | An `import` in the module graph names a missing export (or the module has a static resolution error). Use the preflight to get the real message. |
| Fatal-error dialog, Scripting.log stops mid-run with no error | Uncaught runtime exception in the map script. Bracket the suspect region with `console.log` and relaunch (no restart needed). |
| `execute_js` returns `""` for a valid expression | Result wasn't a string — wrap in `JSON.stringify`. |
| Mod settings ignored after an error dialog | The failed launch reset ALL setup parameters to defaults. Reconfigure. |
