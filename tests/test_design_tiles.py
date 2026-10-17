"""Поле из тайлов: ключ клетки, кодовый художник, сборка кадра, скорость кадра."""
import subprocess
import time
import types

import numpy as np
import pytest
from PySide6.QtGui import QImage

from game.ai.bot import bot_move
from game.core import cells
from game.core.cells import build
from game.core.start import start_field
from game.design import tiles as T
from game.teacher import rules
from game.ui.board import PALETTES, Board
from qt_app import qapp


def dec(grid, rc):
    return T.decode(grid[rc])


def test_encode_decode_round_trip():
    for key in (0, 1, T.N_KEYS - 1, T.encode(T.BODY, 1, 0b0110, 5, 1, 0)):
        d = T.decode(key)
        assert T.encode(**d) == key
    assert len(set(T.common_keys().tolist())) == len(T.common_keys()) == 252


def test_keys_of_the_start_field():
    f = start_field()
    g = T.key_grid(f)
    assert g.shape == f.shape
    for s in (0, 1):
        chain = cells.chain(f, s)
        tail, head = chain[0], chain[-1]
        assert dec(g, tail)["kind"] == T.TAIL and dec(g, tail)["t"] == 0
        assert dec(g, head)["kind"] == T.HEAD and dec(g, head)["snake"] == s
        for a, b in zip(chain, chain[1:]):           # связь видна с обеих сторон
            d = cells.direction(a, b)
            assert dec(g, a)["conn"] >> d & 1 and dec(g, b)["conn"] >> cells.OPPOSITE[d] & 1
        ts = [dec(g, rc)["t"] for rc in chain[:-1]]
        assert ts == sorted(ts)
    long = build(3, 12, [[(1, c) for c in range(11)]])          # змейка из 11 клеток
    ts = [dec(T.key_grid(long), (1, c))["t"] for c in range(10)]
    assert ts[0] == 0 and ts[-1] == 6 and ts == sorted(ts) and len(set(ts)) >= 6
    food = np.argwhere(f == cells.FOOD)[0]
    assert dec(g, tuple(food))["kind"] == T.FOOD
    assert dec(g, (0, 0))["kind"] == T.EMPTY and dec(g, (0, 1))["parity"] == 1
    crashed = T.key_grid(f, (False, True))
    assert dec(crashed, cells.head(f, 1))["crashed"] == 1 and dec(crashed, cells.head(f, 0))["crashed"] == 0


def test_every_whole_snake_key_is_common():
    rng = np.random.default_rng(3)
    common = set(T.common_keys().tolist())
    f = start_field()
    for _ in range(400):
        out = rules.step(f, bot_move(f, 0), bot_move(f, 1), rng)
        f = out.field if out.field is not None else start_field()
        assert set(np.unique(T.key_grid(f)).tolist()) <= common


def test_broken_snake_gets_local_links():
    f = build(5, 5, [[(2, 0), (2, 1), (2, 2)]])
    f[2, 1] = cells.EMPTY                         # сбой: середина пропала
    g = T.key_grid(f)
    tail = dec(g, (2, 0))
    assert tail["kind"] == T.TAIL and tail["conn"] == 1 << cells.RIGHT
    assert dec(g, (2, 2))["kind"] == T.HEAD and dec(g, (2, 2))["conn"] == 0


def test_snake_of_length_one():
    f = build(4, 4, [[(1, 1)], [(2, 2)]])
    g = T.key_grid(f)
    assert dec(g, (1, 1)) == {"kind": T.HEAD, "snake": 0, "conn": 0, "t": 7, "parity": 0, "crashed": 0}
    assert set(np.unique(g).tolist()) <= set(T.common_keys().tolist())


def test_features_shape_and_noise():
    keys = T.common_keys()
    x = T.features(keys, 2, np.full(4, 0.5))
    assert x.shape == (252, T.FEATURES) and np.all(x[:, -4:] == 0.5)
    assert np.all(x[:, :5].sum(1) == 1) and np.all(x[:, T.KINDS + 9 + 2] == 1)


def test_code_tiles_distinguish_kinds():
    qapp()
    keys = T.common_keys()
    for pal in range(len(PALETTES)):
        tiles = T.code_tiles(keys, pal, np.zeros(4))
        assert tiles.shape == (252, 24, 24, 3) and tiles.dtype == np.uint8
        groups = np.array([T.group(k) for k in keys])
        flat = tiles.reshape(252, -1).astype(np.float32)
        for g in np.unique(groups):          # средний тайл вида ближе к своим, чем к чужим
            mean = flat[groups == g].mean(0)
            own = np.abs(flat[groups == g] - mean).mean()
            other = np.abs(flat[groups != g] - mean).mean()
            assert own < other, (pal, g)
        noisy = T.code_tiles(keys, pal, np.ones(4))
        assert np.abs(noisy.astype(int) - tiles).mean() > 0.5        # шум меняет «руку»


def test_compose_puts_tiles_in_place():
    qapp()
    f = start_field()
    g = T.key_grid(f)
    src = T.CodeTiles()
    img = T.compose(src.tiles(0, np.unique(g)), g)
    assert img.shape == (32 * 24, 32 * 24, 3)
    r, c = cells.head(f, 0)
    assert np.array_equal(img[r * 24:(r + 1) * 24, c * 24:(c + 1) * 24], src.tiles(0, [g[r, c]])[int(g[r, c])])


def test_board_draws_what_the_tile_source_gives():
    qapp()

    class Red:
        version = 0

        def tiles(self, palette, keys):
            return {int(k): np.full((24, 24, 3), (255, 0, 0), np.uint8) for k in keys}
    b = Board()
    b.resize(400, 400)
    b.set_state(start_field())
    b.set_tiles(Red())
    img = b.grab().toImage()
    c = img.pixelColor(200, 200)
    assert (c.red(), c.green(), c.blue()) == (255, 0, 0)


OLD_BOARD = subprocess.run(["git", "show", "52947a9:game/ui/board.py"], capture_output=True, text=True,
                           encoding="utf-8").stdout


@pytest.mark.skipif(not OLD_BOARD, reason="нет истории git")
def test_board_frame_not_slower_than_1_1():
    """Кадр матча (поле после хода - одна перерисовка) не медленнее, чем у Board 1.1.0, на
    партии ботов: сравнение лучшего из трёх прогонов."""
    qapp()
    old = types.ModuleType("old_board")
    exec(compile(OLD_BOARD, "old_board", "exec"), old.__dict__)      # noqa: S102 - свой файл из истории
    rng = np.random.default_rng(0)
    f, fields = start_field(), []
    while len(fields) < 300:
        out = rules.step(f, bot_move(f, 0), bot_move(f, 1), rng)
        f = out.field if out.field is not None else start_field()
        fields.append(f)

    def bench(cls):
        b = cls()
        b.resize(700, 700)
        img = QImage(700, 700, QImage.Format.Format_ARGB32)
        t = time.perf_counter()
        for f in fields:
            b.set_state(f)
            img.fill(0)
            b.render(img)
        return time.perf_counter() - t
    bench(Board)
    new, was = min(bench(Board) for _ in range(3)), min(bench(old.Board) for _ in range(3))
    assert new <= was * 1.25, (new, was)
