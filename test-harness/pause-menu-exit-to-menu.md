# Walkthrough: Query the Pause Menu and Exit to Main Menu

A verified, repeatable session (game version of 2026-08-14) that enumerates the
in-game pause (Esc) menu options and programmatically returns the game to the
main menu over the debug port.

All commands below can be sent with `python tests/probe.py '<js>'` or via the
MCP `execute_js` tool.

## 1. Where the menu lives in the game source

The pause menu UI and its handlers are defined in:

```
Base/modules/base-standard/ui-next/screens/pause-menu/pause-menu.js        (buttons + labels)
Base/modules/base-standard/ui-next/screens/pause-menu/pause-menu-model.js  (click handlers)
```

Each button has a `text: "LOC_..."` label key in `pause-menu.js` and a
`handleClick*` function in `pause-menu-model.js`.

## 2. Query the menu options from the live game

The label keys are static, but localization must be resolved live. Batch it in
one call with `Locale.compose`:

```js
JSON.stringify(Object.fromEntries(
  ["LOC_GENERIC_RESUME","LOC_QUICK_SAVE_NAME","LOC_PAUSE_MENU_SAVE",
   "LOC_PAUSE_MENU_LOAD","LOC_PAUSE_MENU_RESTART","LOC_PAUSE_MENU_OPTIONS",
   "LOC_PAUSE_MENU_RETIRE","LOC_END_GAME_EXIT","LOC_PAUSE_MENU_QUIT_TO_DESKTOP"
  ].map(k => [k, Locale.compose(k)])))
```

Verified result:

| Option | LOC key | Handler action |
|---|---|---|
| Resume Game | `LOC_GENERIC_RESUME` | `InterfaceMode.switchToDefault()` |
| Quick Save | `LOC_QUICK_SAVE_NAME` | `SaveLoadData.handleQuickSave()` |
| Save Game | `LOC_PAUSE_MENU_SAVE` | push `screen-save-load` (save mode) |
| Load Game | `LOC_PAUSE_MENU_LOAD` | push `screen-save-load` (load mode) |
| Restart | `LOC_PAUSE_MENU_RESTART` | `Network.restartGame()` after confirm |
| Options | `LOC_PAUSE_MENU_OPTIONS` | push `screen-options` |
| Retire | `LOC_PAUSE_MENU_RETIRE` | `GameContext.sendRetireRequest()` after confirm |
| Exit to Main Menu | `LOC_END_GAME_EXIT` | `engine.call("exitToMainMenu")` after confirm |
| Exit to Desktop | `LOC_PAUSE_MENU_QUIT_TO_DESKTOP` | `engine.call("exitToDesktop")` after confirm |

Some buttons appear conditionally (Retire only while alive, join-code entries
only in multiplayer, etc.).

## 3. Return to the main menu

The confirm dialog is UI-side only — calling the engine function directly
skips it:

```js
engine.call("exitToMainMenu")
```

**Warnings:**

- The game exits to the menu **without saving**. Quick-save first if the
  session matters: `SaveLoadData` is a UI module, so the simplest scripted
  save is the pause menu's own path, or just accept the loss.
- The UI JS context is torn down and reloaded during the transition, so the
  debug connection **drops and must be reconnected**. Expect one dead socket.

## 4. Confirm the state transition

After reconnecting, poll:

```js
UI.isInShell() ? "IN_SHELL" : (UI.isInLoading() ? "LOADING" : "IN_GAME")
```

Verified timing: still `IN_GAME` at ~2s, `IN_SHELL` at ~4s after the call.

## Related engine calls

- `engine.call("exitToDesktop")` — quit the application entirely (confirm
  dialog also bypassed; use deliberately).
