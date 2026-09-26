# Changelog

## 1.0.0 - 2026-09-26 - first release

- Two-player snake on a 32x32 field where a convolutional world network of its own (numpy)
  moves the world: no snake rules in the game code. The teacher with the rules is used only
  while training and is not in the build.
- An opponent network trained by imitating a path-finding bot and then by REINFORCE;
  three levels: novice, medium, strong.
- Qt window: menu, match to three points, statistics with training curves, settings,
  synthesized sounds, the window reopens where it was closed.
