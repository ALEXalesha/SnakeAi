"""Общее для тестов игры: одно приложение Qt на все тесты и поддельные мир и соперник.

Мир в тестах - правила учителя в обёртке с тем же видом, что у WorldNet.step: в tests/
учителя импортировать можно, в игру он не попадает.
"""
import numpy as np
from PySide6.QtWidgets import QApplication

from teacher import rules
from world.cells import heading
from world.net import Result


_APP = []      # держим приложение до конца прогона: без ссылки сборщик мусора убьёт его раньше окон


def qapp():
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    return _APP[0]


class RulesWorld:
    """Мир по правилам учителя; запоминает, какие ходы ему подали."""

    def __init__(self, confidence=0.97):
        self.calls = []
        self.confidence = confidence

    def step(self, field, a0, a1, rng):
        self.calls.append((int(a0), int(a1)))
        out = rules.step(field, a0, a1, rng)
        h, w = field.shape
        probs = np.full((h, w), 1.0 / (h * w))
        return Result(out.field, out.ate, out.crashed, out.food, probs, self.confidence)


class Const:
    """Соперник, который всегда жмёт одно направление."""

    def __init__(self, d):
        self.d = d

    def act(self, field, s):
        return self.d


class Steady:
    """Соперник, который едет прямо."""

    def act(self, field, s):
        return heading(field, s)


class FakeModels:
    """Подмена game.models для окна: мир - правила, соперник - постоянный ход."""

    def __init__(self, opponent=None, passports=None, missing=None):
        self.opponent = opponent if opponent is not None else Const(1)   # вниз - в стену
        self.passports = passports or {}
        self.missing = missing
        self.levels = []

    def load_world(self):
        if self.missing:
            from game.models import ModelMissing
            raise ModelMissing(self.missing)
        return RulesWorld()

    def load_opponent(self, level):
        self.levels.append(level)
        return self.opponent

    def load_passport(self, name):
        return self.passports.get(name)


WORLD_PASSPORT = {
    "final": {"field": 0.996, "events": 0.9993, "food_on_occupied": 0.004},
    "curve": [{"step": i * 100, "loss": 2.0 / (1 + i), "field": 1 - 0.5 / (1 + i),
               "events": 1 - 0.1 / (1 + i), "food_on_occupied": 0.1 / (1 + i)} for i in range(30)],
}

PLAYER_PASSPORT = {
    "levels": {"novice": {"vs_bot": {"win": 0.2}}, "medium": {"vs_bot": {"win": 0.45}},
               "strong": {"vs_bot": {"win": 0.6}}},
    "imitation_curve": [{"step": i * 50, "accuracy": 0.3 + 0.6 * i / 40} for i in range(41)],
    "rl_curve": [{"episode": i, "reward": float(np.sin(i / 5)) + i / 20} for i in range(60)],
}
