# Changelog

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
