import pathlib
import re

import numpy as np

from nn import losses
from world.cells import FOOD, NONE, RIGHT, UP, build
from world.encode import IN_CHANNELS, encode
from world.net import WorldNet
from world.start import start_field

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_encode_one_hot_cells_and_actions():
    f = build(4, 5, [[(0, 0), (0, 1)], [(3, 4), (3, 3)]], food=[(2, 2)])
    x = encode(f[None], np.array([UP]), np.array([NONE]))
    assert x.shape == (1, 4, 5, IN_CHANNELS)
    assert np.all(x[..., :12].sum(axis=-1) == 1)
    assert np.all(x[0, :, :, 12 + UP] == 1) and x[0, :, :, 12:17].sum() == 20
    assert np.all(x[0, :, :, 17 + NONE] == 1) and x[0, :, :, 17:22].sum() == 20
    assert np.all(x[..., -1] == 1)
    assert x[0, 2, 2, FOOD] == 1


def test_encode_batch_keeps_actions_apart():
    f = np.zeros((2, 3, 3), np.int8)
    x = encode(f, np.array([UP, RIGHT]), np.array([NONE, UP]))
    assert x[0, 0, 0, 12 + UP] == 1 and x[1, 0, 0, 12 + RIGHT] == 1
    assert x[0, 0, 0, 12 + RIGHT] == 0


def test_net_runs_on_any_field_size():
    net = WorldNet(hidden=8, glob=4)
    for h, w in [(8, 8), (11, 7), (32, 32)]:
        x = encode(np.zeros((2, h, w), np.int8), np.array([0, 1]), np.array([2, 3]))
        cells, food, events = net.forward(x)
        assert cells.shape == (2, h, w, 12) and food.shape == (2, h, w) and events.shape == (2, 4)


def test_whole_net_gradient_matches_numeric():
    rng = np.random.default_rng(3)
    net = WorldNet(hidden=4, glob=3, rng=rng, dtype=np.float64)
    fields = rng.integers(0, 12, size=(2, 4, 4))
    x = encode(fields, np.array([0, 4]), np.array([2, 1]), dtype=np.float64)
    tc = rng.integers(0, 12, size=(2, 4, 4))
    tf = rng.integers(0, 16, size=2)
    te = rng.integers(0, 2, size=(2, 4)).astype(float)

    def loss():
        cells, food, events = net.forward(x)
        a, dc = losses.softmax_xent(cells, tc)
        b, dfd = losses.softmax_xent(food.reshape(2, -1), tf)
        c, de = losses.bce(events, te)
        return a + b + c, dc, dfd.reshape(food.shape), de

    _, dc, dfd, de = loss()
    net.backward(dc, dfd, de)
    eps = 1e-5
    for name, p, g in net.params():
        idx = tuple(rng.integers(0, s) for s in p.shape)
        old = p[idx]
        p[idx] = old + eps
        up = loss()[0]
        p[idx] = old - eps
        down = loss()[0]
        p[idx] = old
        np.testing.assert_allclose(g[idx], (up - down) / (2 * eps), rtol=1e-4, atol=1e-8,
                                   err_msg=name)


def test_step_is_deterministic_for_one_seed():
    net = WorldNet(hidden=8, glob=4)
    f = start_field(8, 8)
    a = net.step(f, UP, NONE, np.random.default_rng(5))
    b = net.step(f, UP, NONE, np.random.default_rng(5))
    assert a.crashed == b.crashed
    if a.field is not None:
        np.testing.assert_array_equal(a.field, b.field)
    assert abs(a.food_probs.sum() - 1) < 1e-9
    assert 0 <= a.confidence <= 1


def test_save_load_gives_same_outputs(tmp_path):
    net = WorldNet(hidden=8, glob=4, rng=np.random.default_rng(1))
    x = encode(start_field(8, 8)[None], np.array([UP]), np.array([NONE]))
    path = tmp_path / "w.npz"
    net.save(path)
    back = WorldNet.load(path)
    for a, b in zip(net.forward(x), back.forward(x)):
        np.testing.assert_array_equal(a, b)


def test_game_and_world_never_import_the_teacher():
    """Главное условие проекта: в игре нет кода правил."""
    for folder in ("world", "game", "player", "nn"):
        for path in (ROOT / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+teacher", text, re.M), path
    main = ROOT / "main.py"
    if main.exists():
        assert "teacher" not in main.read_text(encoding="utf-8")
