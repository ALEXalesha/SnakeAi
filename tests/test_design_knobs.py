"""Шум оформления: z = 0 - ровно окно 1.1.0, любой шум сохраняет контраст текста."""
import colorsys
import itertools
import subprocess

import numpy as np
import pytest

from game.design import knobs as K
from game.ui import theme

OLD_THEME = subprocess.run(["git", "show", "52947a9:game/ui/theme.py"], capture_output=True, text=True,
                           encoding="utf-8").stdout


def old_qss(name):
    ns = {}
    exec(compile(OLD_THEME, "old_theme", "exec"), ns)          # noqa: S102 - свой файл из истории
    return ns["qss"](name)


@pytest.mark.skipif(not OLD_THEME, reason="нет истории git")
@pytest.mark.parametrize("name", theme.THEMES)
def test_zero_noise_is_the_old_look(name):
    zero = np.zeros(K.Z_DIM)
    assert theme.qss(name) == old_qss(name)
    assert theme.qss(name, K.code_style(theme.tokens(name), zero)) == old_qss(name)


def test_knobs_ranges():
    lo, hi = K.knobs(-np.ones(4)), K.knobs(np.ones(4))
    assert (lo.margin, hi.margin) == pytest.approx((0.75, 1.25))
    assert (lo.spacing, hi.spacing) == pytest.approx((0.7, 1.3))
    assert (lo.font, hi.font) == pytest.approx((0.95, 1.05))
    assert (lo.radius, hi.radius) == pytest.approx((7, 13))
    assert (lo.hue, hi.hue) == pytest.approx((-14, 14))
    assert K.knobs(np.full(4, 5.0)) == hi                      # шум за пределами обрезается
    z = K.sample_z(np.random.default_rng(1))
    assert z.shape == (4,) and np.all(np.abs(z) <= 1)


def test_style_vector_round_trip():
    z = np.array([0.3, -0.7, 0.9, -0.4])
    style = K.code_style(theme.tokens("light"), z)
    v = K.style_vector(style)
    assert v.shape == (K.STYLE_DIM,)
    back = K.style_from_vector(v)
    assert back["font"] == pytest.approx(style["font"]) and back["radius"] == pytest.approx(style["radius"])
    assert back["colors"] == style["colors"]


GRID = list(itertools.product((-1.0, -0.5, 0.0, 0.5, 1.0), repeat=4))


@pytest.mark.parametrize("name", theme.THEMES)
def test_code_style_keeps_contrast(name):
    for z in GRID:
        t = theme.tokens(name, K.code_style(theme.tokens(name), np.array(z)))
        assert K.contrast(t["text"], t["bg"]) >= 4.5
        assert K.contrast(t["text"], t["card"]) >= 4.5
        assert K.contrast(t["muted"], t["bg"]) >= 3
        assert K.contrast(t["accent_text"], t["accent"]) >= 3, (z, t["accent"])
        assert K.contrast(t["title"], t["bg"]) >= 3, (z, t["title"])


def test_hue_rotation_keeps_lightness():
    for color in ("#2fbf71", "#1f9d5a", "#7ee2a8"):
        for deg in (-14, -5, 7, 14):
            a = colorsys.rgb_to_hls(*K._rgb(color))
            b = colorsys.rgb_to_hls(*K._rgb(K.rotate_hue(color, deg)))
            assert b[1] == pytest.approx(a[1], abs=0.01) and b[2] == pytest.approx(a[2], abs=0.03)
            assert K.rotate_hue(color, deg) != color


def test_contrast_extremes():
    assert K.contrast("#000000", "#ffffff") == pytest.approx(21)
    assert K.contrast("#123456", "#123456") == pytest.approx(1)
