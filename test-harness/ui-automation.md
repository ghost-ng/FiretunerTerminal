# Shell UI Automation (Playwright-style)

Driving the game's cohtml UI from `execute_js`: querying screens, pressing
buttons, dismissing dialogs. Verified against the create-game flow.

## The one thing that matters: synthetic DOM events do NOT work

`el.click()`, full `MouseEvent` sequences, and `action-activate`
CustomEvents are all ignored by game buttons. Input is routed through the
engine layer. Buttons (ui-next `Activatable`: hero buttons, tiles, close
buttons) listen for the engine's `engine-input` CustomEvent **on the element
itself** and activate on `mousebutton-left` with a START→FINISH pair:

```js
function pressButton(el) {
  const mk = (status) => new CustomEvent('engine-input', {
    bubbles: true, cancelable: true,
    detail: { name: 'mousebutton-left', status, x: -1, y: -1,
              isTouch: false, isMouse: true }
  });
  el.dispatchEvent(mk(InputActionStatuses.START));   // 0 — press
  el.dispatchEvent(mk(InputActionStatuses.FINISH));  // 1 — release → onActivate
}
```

- `InputActionStatuses` = `{START:0, FINISH:1, UPDATE:2, HOLD:3, DRAG:4}`
  (global in the UI context).
- Activation fires on FINISH. Alternative accepted names: `keyboard-enter`,
  `touch-tap`.
- Source of truth: `core/ui-next/components/activatable.js` (onEngineInput).
- Old-framework components (`fxs-text-button` on the main menu) accept the
  same `engine-input` pattern.

## Finding your way around

```js
// Screen stack — which screens are mounted
Array.from(document.querySelectorAll('.fullscreen > *')).map(e => e.tagName)
// e.g. ["MAIN-MENU"] or ["MAIN-MENU","MOUSE-GUARD","CREATE-GAME-SP",...]

// Primary action buttons (Continue / Confirm / Launch Game / Select)
Array.from(document.querySelectorAll('div.hero-button-2'))
  .map(el => (el.textContent || '').trim())

// Anything activatable, labeled
Array.from(document.querySelectorAll('[data-activatable="true"]'))
  .map(el => (el.textContent || '').trim()).filter(Boolean)

// Modal dialogs (fatal errors, confirmations)
(document.querySelector('screen-dialog-box')?.textContent || '').trim()
```

## Create-game flow map (single player)

```
MAIN MENU ──"NEW GAME" (fxs-text-button)──► CIV SELECT
  civ tiles are [data-activatable]; press one, then hero "Select"
CIV/LEADER pages ──"Select"/"Continue" (hero-button-2)──► GAME SETUP
  6 × .create-game-setup-box (Difficulty / Map Type / Speed / Map Size / ...)
GAME SETUP ──"Continue"──► OVERVIEW ──"Launch Game"──► loading → in game
```

Generic stepper — press the visible hero button until Launch appears:

```js
for (let i = 0; i < 8; i++) {
  const bs = Array.from(document.querySelectorAll('div.hero-button-2'))
    .map(el => ({el, t: (el.textContent||'').trim()}));
  if (bs.find(b => b.t === 'Launch Game')) break;
  const next = bs.find(b => ['Select','Continue','Next','Confirm'].includes(b.t)) ?? bs[0];
  if (next) pressButton(next.el);
}
```

Configure via `GameSetup` (see game-api-testing.md) — only use UI presses
for flow transitions. The advanced-options "Confirm" button applies nothing;
it only closes the popup (`popupContext.close`), so API-written values are
already live before it's pressed.

## Full launch cycle (verified end-to-end)

```
NEW GAME → [flow steps] → Launch Game → (loading) → "Begin Game" button
  → in game → ... → engine.call("exitToMainMenu") → clean MAIN-MENU
```

- **Begin Game**: loading ends at a hold screen; press its button (same
  engine-input pattern) to actually start. `UI.isInGame()` is already true
  at that screen — map queries work before pressing it.
- **Exit**: `engine.call("exitToMainMenu")` works from anywhere in-game and
  needs no dialog handling. (Found in base `ui/automation/` scripts, which
  are themselves a good reference for game-flow automation.)

## Hotseat / multiplayer flow (verified end-to-end via CDP 9444)

The tuner port closes in MP (see mcp-testing.md) — the terminal and MCP
server now fall back to the Cohtml CDP debugger automatically, so the same
tools/JS patterns keep working; expect a one-time ~30s stall on the first
command after the lobby opens (zombie-socket detection). The tuner listener
reopens on exiting the MP session to the main menu (leaving the lobby via
its Back button is enough) and the connection switches back by itself.

```
MAIN MENU --MULTIPLAYER (fxs-text-button)--> SCREEN-MP-LANDING
  --.mp-landing-new__hotseat-button (action-activate)--> SCREEN-MP-CREATE-GAME
  --GameSetup config (the Map param here is the SupportsSinglePlayer="0" row)--
  --fxs-hero-button caption LOC_UI_MP_HOST_LOBBY (action-activate)--> SCREEN-MP-LOBBY
```

In the lobby:

```js
// Add human slots (SS_TAKEN = human). Direct property assignment is
// silently ignored -- must use the setter:
Configuration.editPlayer(1).setSlotStatus(SlotStatus.SS_TAKEN);
// SlotStatus: {SS_OPEN:0, SS_COMPUTER:1, SS_CLOSED:2, SS_TAKEN:3, SS_OBSERVER:4}

// Launch: press the Ready toggle
document.querySelector('screen-mp-lobby fxs-activatable.ready-button')
```

After loading, hotseat inserts a **turn-transition screen** with plain
`.fxs-button` divs labeled "Save Game" / **"Start Turn"** -- press Start
Turn to enter the active player's turn (appears between every player's
turn, not just the first).

Notes:
- GameSetup config applied in the CREATE-GAME screen survived into the
  lobby in scripted runs -- but re-verify in the lobby; manual fiddling has
  reset it before.
- Engine behavior found this way: `bHumansTogether`
  (assign-starting-plots.js) forces all humans onto the largest landmass
  when the age has `HumanPlayersPrimaryHemisphere` (Antiquity does) -- mods
  wanting separated humans must re-place them post-assignment via
  `StartPositioner.setStartPosition` swaps.

## Dialogs

Fatal-error dialogs (`SCREEN-DIALOG-BOX` in the stack) block everything.
Dismiss:

```js
const ok = Array.from(document.querySelectorAll(
    '[data-activatable="true"], div.hero-button-2, fxs-button'))
  .find(el => (el.textContent || '').trim() === 'OK');
if (ok) pressButton(ok);
```

After a fatal map-gen error dialog, the create-game flow is fully closed
AND all setup parameters are reset — restart from NEW GAME and reconfigure.

## Styling / decorating game UI

- Elements render inline styles via Solid; to override, set styles directly
  and re-apply from a `MutationObserver` (childList + attributes filtered
  to `style`). Guard re-sets by substring comparison — the style getter
  normalizes URL quoting, so exact-string guards loop forever.
- Mod files are served at `fs://game/<mod id lowercased>/<path>` once
  listed in an `<ImportFiles>` action.
