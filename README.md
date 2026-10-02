<div align="center">

# Neuro Snake

**Two-player snake with not a single line of snake rules: the world is moved by a convolutional network of its own, and a second network plays against you.**

[Download for Windows](https://github.com/ALEXalesha/SnakeAi/releases/latest) &nbsp;·&nbsp; [Русская версия этого файла](README.ru.md)

[![CI](https://github.com/ALEXalesha/SnakeAi/actions/workflows/ci.yml/badge.svg)](https://github.com/ALEXalesha/SnakeAi/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ALEXalesha/SnakeAi?color=16a34a)](https://github.com/ALEXalesha/SnakeAi/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<img src="docs/preview_match.png" width="900" alt="A match: the green snake is the player, the orange one is the network">

</div>

> **The interface is in Russian**, and so is the long write-up - [README.ru.md](README.ru.md), which this file summarises.

A 32x32 field, two snakes: green is yours (arrows or WASD), orange is a neural network. Hit a wall, a body or the other head and the round is over; the survivor scores, first to three wins.

The point is invisible. A normal snake game has code that moves the head, checks the walls, grows the tail after eating and drops new food. **This one has none of it.** Every tick the game hands the old field and both key presses to a *world network*, and the network returns the new field: where the snakes moved, who ate, who crashed and where the next food appears. The game only draws what the network said, keeps score and reads keys.

## The world network

Each cell is one of 12 classes. A body cell stores not "how many ticks it has left" but a **pointer to the neighbour closer to the head**, which makes every rule local: the tail is the body cell nobody points to, the neck points at the head and gives the heading, and the snake's length never enters the rules, so a network trained on short snakes carries a hundred-cell one just as well.

Three 3x3 convolutions (a 7x7 view around every cell) plus one long-range link, a global max over the field, which exists for a single rule: "the snake ate, so its tail stays", where the eating happens at the head and the tail may be across the field. Separate outputs give each cell's class, four events (who ate, who crashed) and a map of where food will appear; the new food is drawn from it. Field size is not baked in.

The rules live only in a *teacher* (`teacher/`, plain code) used while training: it plays bot games and grows random snakes to make examples. Training ran on 8-16 cell fields (a convolution on 12x12 is seven times cheaper than on 32x32) mixed with 32x32 ones, on hand-written numpy layers. A single pass on held-out 32x32 fields matches the teacher cell for cell on 99.8% of moves - one slip per 500 moves, and a slip leaves a stray piece of snake on the field for good. So in the game the network looks at the field eight times, in four rotations and two mirror images in one batch, and adds the answers back in place: snake rules do not change under rotation (a test checks this on the teacher), the network's rare slips do not repeat across views, and the result is **100% of moves** on the same fields at 22 ms per move. Still only the network - just a permutation of cells and direction names. The teacher is not in the build, and a test checks the sources that neither the game nor the world network imports it.

## The opponent

It sees a 15x15 window around its head, the direction to the nearest food and its own heading; a dense network 906 -> 128 -> 64 -> 4 picks the direction. No "don't hit the wall" check exists in the game. It learned first by imitating a path-finding bot (96.6% agreement), then by REINFORCE against that bot, kept only if it loses no more often.

| Level | vs bot: wins / losses / draws | vs a random snake |
|---|---|---|
| novice (early imitation snapshot) | 3% / 74% / 23% | 99% wins |
| medium (imitation) | 12% / 40% / 48% | 100% |
| strong (after reinforcement) | 9% / 29% / 62% | 100% |

## The window

<img src="docs/preview_menu.png" width="440" alt="Menu"> <img src="docs/preview_stats.png" width="440" alt="Statistics">

Qt (PySide6): menu, match with a 3-2-1 countdown and pause, statistics with both networks' training curves, settings (speed, opponent level, volume, three palettes, a food-map overlay), synthesized sounds, and the window reopens where it was closed.

## Running

Download `SnakeAIGame-<version>-portable.zip` or `-setup.exe` from the [releases](https://github.com/ALEXalesha/SnakeAi/releases/latest), or from source with Python 3.13:

```
pip install -r requirements.txt
python main.py
```

Retrain with `python -m train.world_train` and `python -m train.player_train`; build with `python build.py`.

## Tests

`python -m pytest -q` - 163 tests: layers against numeric gradients, every teacher rule, the trained world network against the teacher on held-out fields, long snakes and whole rounds, the opponent against the bot, and the window off-screen. Deliberately broken rules, gradients and key queues turn them red.

Python, numpy, PySide6. MIT licence.
