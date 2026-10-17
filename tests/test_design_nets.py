"""Сети-оформители: градиенты, сохранение, формат входа и выхода (без обученных моделей)."""
import numpy as np
import pytest

from aikit.nn.gradcheck import check_layer
from game.design import designer_net as D
from game.design.knobs import STYLE_DIM, code_style, style_vector
from game.design.mlp import MLP
from game.design.painter_net import OUT, PainterNet
from game.design.tiles import FEATURES, common_keys
from game.ui import theme


def test_mlp_gradients_with_and_without_sigmoid():
    rng = np.random.default_rng(0)
    for squash in (False, True):
        net = MLP((5, 7, 6, 4), squash=squash, rng=rng)
        for _, p, _ in net.params():
            p[...] = p.astype(np.float64)
        net.net.items = [_f64(layer) for layer in net.net.items]
        check_layer(_Wrap(net), rng.normal(size=(3, 5)), rng, rtol=1e-3, atol=1e-5)


class _Wrap:
    def __init__(self, net):
        self.net = net

    def forward(self, x):
        return self.net.forward(x)

    def backward(self, dy):
        return self.net.backward(dy)

    def params(self):
        return self.net.params()


def _f64(layer):
    for name in ("W", "b", "dW", "db"):
        if hasattr(layer, name):
            setattr(layer, name, getattr(layer, name).astype(np.float64))
    return layer


def test_painter_save_load_and_shape(tmp_path):
    net = PainterNet(hidden=32, rng=np.random.default_rng(1))
    tiles = net.draw(common_keys()[:5], 1, np.zeros(4))
    assert tiles.shape == (5, 24, 24, 3) and tiles.dtype == np.uint8
    net.save(tmp_path / "p.npz")
    back = PainterNet.load(tmp_path / "p.npz")
    assert np.array_equal(back.draw(common_keys()[:5], 1, np.zeros(4)), tiles)
    assert back.mlp.sizes == (FEATURES, 32, 32, OUT)


def test_wrong_file_is_refused(tmp_path):
    MLP((3, 4, 5)).save(tmp_path / "x.npz")
    with pytest.raises(ValueError):
        PainterNet.load(tmp_path / "x.npz")
    with pytest.raises(ValueError):
        D.DesignerNet.load(tmp_path / "x.npz")


def test_nan_weights_are_refused(tmp_path):
    net = PainterNet(hidden=8)
    net.params()[0][1][0, 0] = np.nan
    net.save(tmp_path / "nan.npz")
    with pytest.raises(ValueError):
        PainterNet.load(tmp_path / "nan.npz")


def test_designer_slots_match_the_screens():
    from aikit.host import Context
    from game.ui.sound import Sounds
    from game.ui.widget import GameWidget
    from qt_app import FakeModels, qapp
    import tempfile
    qapp()
    w = GameWidget(Context(tempfile.mkdtemp(), "dark", "ru", 0), FakeModels(), sounds=Sounds(enabled=False),
                   design=False)
    for screen in w.screens:
        assert screen.NAME in D.SCREENS
        assert tuple(n for n, _, _ in screen.elements()) == D.SLOTS[screen.NAME]
    w.close()


def test_designer_target_and_rects_round_trip():
    rects = {"title": (28, 22, 160, 40), "back": (900, 20, 100, 42), "scroll": (28, 80, 980, 600)}
    style = style_vector(code_style(theme.tokens("dark"), np.zeros(4)))
    y, m = D.target("stats", rects, style)
    assert y.shape == (D.OUT,) and m[:12].all() and not m[12:4 * D.MAX_SLOTS].any()
    back = D.rects_from("stats", y)
    r = D.ROOM
    assert back["title"] == (28 - r, 22 - r, 160 + 2 * r, 40 + 2 * r)
    assert np.allclose(y[4 * D.MAX_SLOTS:], style) and len(style) == STYLE_DIM


def test_designer_inputs():
    x = D.inputs("settings", 1040, 720, "light", "en", (1, 0), np.full(4, 0.25))
    assert x.shape == (D.IN,) and x[0] == pytest.approx(1.04) and x[2 + 3] == 1 and x[7] == 1 and x[9] == 1
    assert x[10] == 1 and x[11] == 0 and np.all(x[12:] == 0.25)
