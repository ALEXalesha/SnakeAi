# Changelog

## 2.0.0 - 2026-10-17

The rules were already a network; now the window and the board picture are too. The coded
version stays only as the teacher and the fallback.

- **Designer network** (`game/design/designer_net.py`, dense 16-384-384-69, own numpy layers):
  from the screen, window size, theme, language, visible optional items and four noise numbers
  it outputs a rectangle for every element of the screen and the window style (font scale,
  corner radius, five accent colours). The widgets stay real Qt widgets; in AI mode the
  screen's top layouts are switched off and every element gets `setGeometry` from the
  network. Teacher: the 1.x layouts themselves in offscreen Qt on 2400 window sizes from
  820x600 to 3840x2160, both languages, five font sizes, with code knobs following the same
  noise (margins, spacing, font, radius, accent hue) - 19 200 layouts, 0.67 px mean error,
  99.8% of 1200 held-out layouts pass the laws.
- **Painter network** (`game/design/painter_net.py`, 21-384-384-1728): paints every board cell
  as a 24x24 RGB tile from a cell key (empty, food, body, head, tail; whose snake; links to
  neighbours; place along the snake; checker parity; crash), the palette and noise. Teacher:
  a coded tile painter drawing what 1.x drew; tiles differ from it by 0.73% on average (worst
  2.3%). Board frames redraw only the cells whose key changed - no slower than 1.1 (a test).
- **Laws and fallback** (`game/design/laws.py`, `runtime.py`): inside the window and the
  parent, no overlaps, room for the text (`heightForWidth` for wrapped lines), buttons at least
  28 px, the board at least 320 px, WCAG contrast; every tile looks most like a coded tile of
  its own kind and differs from it by at most 4%. On failure up to three new noises, then the
  coded layout for the same noise, then the plain 1.1 layout; everything is logged silently
  to `ai_ui.json`. In 240 launches over six window sizes the fallback was never needed.
- **Statistics**: a new card shows how far the window is from the coded one on average and
  how many times the fallback was used for the window and the board, plus the training
  curves of both new networks.
- **Settings** fill the whole window in two cards (Game; Look and sound), like Statistics -
  in 1.1 they were a narrow column in the top-left corner.
- Found on the way, each with a test: the code packs elements tight to their minimum size,
  so the designer trains on rectangles with 1 px of room and an 8x penalty for undersizing
  (78% -> 99.8% of layouts pass); settings hints keep room for three lines; the font is one
  of five sizes; on a language switch the designer gets the new language together with the
  new texts (the self-check caught a screen stuck on the fallback); OpenBLAS on 4 threads in
  training (16 threads next to other processes made the painter 25 times slower).
- Training: `python -m game.train.paint_train` (about 25 min) and
  `python -m game.train.design_train` (about 17 min). The self-check (`--selftest`) also lays
  out every screen and paints the board through the networks.
- Tests: 313 (222 of the game and 91 of `aikit`); `tools/mutate.py` - deliberate breakages of
  the laws, the fallback, the journal, the tiles and the settings layout, all caught.

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
