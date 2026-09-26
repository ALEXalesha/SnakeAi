"""Сеть-мир: по старому полю и двум ходам выдаёт новое поле, события и карту новой еды.

    вход 23 -> Conv3x3 48 -> ReLU -> Conv3x3 48 -> ReLU -> Conv3x3 48 -> ReLU = F   (местное)
    F -> максимум по полю -> Dense 32 -> ReLU = g                                    (общее)
        g -> Dense 4  : логиты событий «0 съела», «1 съела», «0 врезалась», «1 врезалась»
        g -> Dense 48 : добавка ко всем клеткам F (так хвост узнаёт, что его змейка съела)
    (F + добавка) -> 1x1 48 -> ReLU -> 1x1 13 : 12 классов клетки + оценка «здесь еда»

Поле зрения местной части 7x7 - на все местные правила хватает; размер поля не зашит.
"""
from typing import NamedTuple, Optional

import numpy as np

from nn import io
from nn.layers import Conv1x1, Conv3x3, Dense, GlobalMax, ReLU
from nn.losses import sigmoid, softmax
from world.cells import FOOD, N_CLASSES
from world.encode import IN_CHANNELS, encode

EVENTS = ("ate0", "ate1", "crash0", "crash1")


class Result(NamedTuple):
    field: Optional[np.ndarray]   # None - кто-то врезался, раунд окончен
    ate: tuple
    crashed: tuple
    food: Optional[tuple]
    food_probs: np.ndarray        # (H, W) - где сеть родила бы еду
    confidence: float             # вероятность выбранного класса в самой неуверенной клетке


class WorldNet:
    def __init__(self, hidden=48, glob=32, rng=None, dtype=np.float32):
        rng = np.random.default_rng(0) if rng is None else rng
        self.hidden, self.glob = hidden, glob
        L = {}
        L["c1"] = Conv3x3(IN_CHANNELS, hidden, rng, dtype)
        L["c2"] = Conv3x3(hidden, hidden, rng, dtype)
        L["c3"] = Conv3x3(hidden, hidden, rng, dtype)
        L["g1"] = Dense(hidden, glob, rng, dtype)
        L["ev"] = Dense(glob, len(EVENTS), rng, dtype)
        L["bc"] = Dense(glob, hidden, rng, dtype)
        L["c4"] = Conv1x1(hidden, hidden, rng, dtype)
        L["c5"] = Conv1x1(hidden, N_CLASSES + 1, rng, dtype)
        self.layers = L
        self.r = [ReLU() for _ in range(5)]
        self.gmax = GlobalMax()
        self.dtype = dtype

    def params(self):
        return [(f"{n}.{p}", a, g) for n, l in self.layers.items() for p, a, g in l.params()]

    def forward(self, x):
        L, r = self.layers, self.r
        f = r[0].forward(L["c1"].forward(x))
        f = r[1].forward(L["c2"].forward(f))
        f = r[2].forward(L["c3"].forward(f))
        g = r[3].forward(L["g1"].forward(self.gmax.forward(f)))
        events = L["ev"].forward(g)
        z = f + L["bc"].forward(g)[:, None, None, :]
        out = L["c5"].forward(r[4].forward(L["c4"].forward(z)))
        return out[..., :N_CLASSES], out[..., N_CLASSES], events

    def backward(self, d_cells, d_food, d_events):
        L, r = self.layers, self.r
        d_out = np.concatenate([d_cells, d_food[..., None]], axis=-1).astype(self.dtype)
        dz = L["c4"].backward(r[4].backward(L["c5"].backward(d_out)))
        dg = L["bc"].backward(dz.sum(axis=(1, 2))) + L["ev"].backward(d_events.astype(self.dtype))
        df = dz + self.gmax.backward(L["g1"].backward(r[3].backward(dg)))
        df = L["c3"].backward(r[2].backward(df))
        df = L["c2"].backward(r[1].backward(df))
        return L["c1"].backward(r[0].backward(df))

    def predict(self, field, a0, a1):
        """Прогон сети на одном поле: (классы нового поля по argmax, события, вероятности
        классов, карта еды) - без выбора новой еды."""
        x = encode(field[None], np.array([a0]), np.array([a1]))
        cells, food, events = self.forward(x.astype(self.dtype))
        ev = sigmoid(events[0].astype(np.float64)) > 0.5
        probs = softmax(cells[0].astype(np.float64))
        H, W = field.shape
        food_probs = softmax(food[0].reshape(-1).astype(np.float64)).reshape(H, W)
        return probs.argmax(axis=-1).astype(np.int8), ev, probs, food_probs

    def step(self, field, a0, a1, rng):
        """Один ход мира сетью. Кода правил здесь нет: только прогон и выбор по выходам."""
        new, ev, probs, food_probs = self.predict(field, a0, a1)
        confidence = float(probs.max(axis=-1).min())
        crashed = (bool(ev[2]), bool(ev[3]))
        ate = (bool(ev[0]), bool(ev[1]))
        if any(crashed):
            return Result(None, (False, False), crashed, None, food_probs, confidence)
        spot = None
        if any(ate):
            H, W = field.shape
            k = int(rng.choice(H * W, p=food_probs.reshape(-1)))
            spot = (k // W, k % W)
            new[spot] = FOOD
        return Result(new, ate, crashed, spot, food_probs, confidence)

    def save(self, path):
        arrays = io.collect(self.layers)
        arrays["meta.shape"] = np.array([self.hidden, self.glob])
        io.save(path, arrays)

    @classmethod
    def load(cls, path):
        arrays = io.load(path)
        hidden, glob = (int(v) for v in arrays["meta.shape"])
        net = cls(hidden, glob)
        io.restore(net.layers, arrays)
        return net
