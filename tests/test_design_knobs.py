"""Шум оформления: z = 0 - ровно основной вид окна (без шума), любой шум сохраняет контраст текста.

До 2.1 основной вид был видом 1.1.0 (сверка с theme.py из истории git); с 2.1 у змейки свой вид
«террариум» (правило автора 17.10: меню, настройки и статистика у каждой игры свои), и z = 0 -
этот вид: таблица стилей без шума та же, что у стиля кода с нулевым шумом."""
import colorsys
import itertools

import numpy as np
import pytest

from game.design import knobs as K
from game.ui import theme


@pytest.mark.parametrize("name", theme.THEMES)
def test_zero_noise_is_the_base_look(name):
    zero = np.zeros(K.Z_DIM)
    assert theme.qss(name, K.code_style(theme.tokens(name), zero)) == theme.qss(name)
    assert K.code_style(theme.tokens(name), zero)["colors"]["accent"] == theme.TOKENS[name]["accent"]


def test_knobs_ranges():
    lo, hi = K.knobs(-np.ones(4)), K.knobs(np.ones(4))
    assert (lo.margin, hi.margin) == pytest.approx((0.8, 1.2))
    assert (lo.spacing, hi.spacing) == pytest.approx((0.85, 1.15))
    assert (lo.font, hi.font) == pytest.approx((0.96, 1.04))
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
