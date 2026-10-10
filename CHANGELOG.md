# Changelog

## 1.1.0 - 2026-10-10

The game follows the PythonAiGames contract: the same game opens in its own window and in a
tab of the AiGameRoom game room, with no adapter.

- Everything game-specific is in `game/`: `core/` (field encoding, symmetries, start, match),
  `ai/` (world network, opponent, model loading), `teacher/` and `train/` (training only:
  `python -m game.train.world_train`), `ui/` (the widget), `models/`. `game/__init__.py`
  exports `GAME_INFO` and `create_widget(ctx)`. A test still checks that no game code imports
  the teacher.
- The game has no main window of its own: the standalone window comes from the shared
  `aikit` kit (copy 0.1.0). Window size, the Quit button and the look are as in 1.0.1: menu
  and statistics screenshots match the old ones pixel for pixel.
- English: the whole interface in Russian and English, switched in the settings at once.
  A light theme next to the dark one. Theme and language also follow the shell on the fly.
- Volume, theme and language are shared (`ctx`). Data now lives in `%APPDATA%\SnakeAIGame`;
  settings, statistics and window place of 1.0.x from `%LOCALAPPDATA%\SnakeAIGame` are copied
  there on the first start (the old files stay).
- In a shell tab: `pause()` pauses the match and stops its timer, `resume()` restarts the
  clock (the match waits for Continue), `shutdown()` stops the timer.
- Sounds are written to the data folder instead of a temporary one; with no screen (tests,
  self-check, contract check) there is no sound, which also fixes the contract check hanging
  on an output channel QtMultimedia kept open.
- numpy layers, the standalone window and the window state come from `aikit`; the own `nn/`,
  `game/paths.py` and `game/window_state.py` are gone.
- Tests: 244 (153 of the game and 91 of `aikit`), new `tests/test_contract.py`; eleven
  deliberate breakages of the widget are all caught. The shell's `tools/contract_check.py
  --run`: 0 errors.

## 1.0.1 - 2026-09-26

- The end-of-round caption on the field ("Раунд ваш!", "Раунд за сетью", "Ничья") and the
  3-2-1 countdown are 1.5 times smaller: the font is 9.3% of the field height instead of 14%,
  and "Раунд за сетью" takes 68% of the field width instead of 104% (it no longer ran past
  the field edges). A test keeps the caption within 10% of the field height and 75% of its
  width, fitting whole with 10% wider fonts, in the usual and the minimum window.

## 1.0.0 - 2026-09-26 - first release

- Two-player snake on a 32x32 field where a convolutional world network of its own (numpy)
  moves the world: no snake rules in the game code. The teacher with the rules is used only
  while training and is not in the build.
- An opponent network trained by imitating a path-finding bot and then by REINFORCE;
  three levels: novice, medium, strong.
- Qt window: menu, match to three points, statistics with training curves, settings,
  synthesized sounds, the window reopens where it was closed.
