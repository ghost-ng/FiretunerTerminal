# Tests & Exploration Notes

Verified walkthroughs and tooling for probing the Civ7 debug port. Everything
here was executed against a live game and recorded with actual results.

## Contents

- **[probe.py](probe.py)** — minimal synchronous client for the debug port.
  `python tests/probe.py 'GameplayMap.getGridWidth()'` sends one expression
  and prints the response; import `Probe` for scripted sessions.
- **[api-crawling.md](api-crawling.md)** — methodology for discovering and
  validating API functions and calls: static crawling of the game's source
  maps/JS (and the grep pitfalls), live prototype-chain enumeration, batch
  probing, and the validation rules for trusting results.
- **[pause-menu-exit-to-menu.md](pause-menu-exit-to-menu.md)** — worked
  example: enumerate the in-game pause menu options and return to the main
  menu via `engine.call("exitToMainMenu")`.

## Prerequisites

The game must be running with the debug port enabled (TCP 4318). Gameplay
globals (`GameplayMap`, `Players`, `Game`, ...) only exist once a save is
loaded — at the main menu you get the shell context only (`UI`,
`Configuration`, `GameContext`, `engine`, `Locale`).
