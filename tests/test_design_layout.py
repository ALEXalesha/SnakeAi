"""Раскладка кода как учитель: снимок, применение, законы."""
import numpy as np
import pytest
from PySide6.QtTest import QTest

from aikit.host import Context
from game.design import layout as L
from game.design.knobs import code_style, knobs
from game.design.laws import check_layout, check_style
from game.ui import theme
from game.ui.sound import Sounds
from game.ui.widget import GameWidget
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, FakeModels, qapp


def make(tmp_path, th="dark", lang="ru"):
    qapp()
    w = GameWidget(Context(tmp_path / f"data-{th}-{lang}", th, lang, 60),
                   FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}),
                   sounds=Sounds(enabled=False), design=False)
    w.resize(1040, 720)
    w.show()
    return w


def screens(w):
    return ((w.menu, w.show_menu), (w.match_screen, w.play), (w.stats_screen, w.show_stats),
            (w.settings_screen, w.show_settings))


def set_style(w, th, z):
    style = code_style(theme.tokens(th), z)
    w.style_now, w.theme_name = style, th
    w.restyle()                                   # масштаб окна ставит сам виджет при resize
    k = knobs(z)
    for s in w.screens:
        s.set_knobs(k)
    return style


@pytest.mark.parametrize("th,lang", [("dark", "ru"), ("light", "en")])
def test_code_layout_obeys_the_laws(tmp_path, th, lang):
    w = make(tmp_path, th, lang)
    rng = np.random.default_rng(7)
    zs = [np.zeros(4), -np.ones(4), np.ones(4), rng.uniform(-1, 1, 4)]
    sizes = [(820, 600), (1040, 720), (3840, 2160)] + L.sample_sizes(rng, 9)
    for z in zs:
        style = set_style(w, th, z)
        assert check_style(theme.tokens(th, style)) == []
        for screen, show in screens(w):
            show()
            for size in sizes:
                w.resize(*size)
                QTest.qWait(1)
                rects = L.capture(screen)
                assert check_layout(screen, rects) == [], (screen.__class__.__name__, size, z)
    w.close()


def test_apply_of_captured_is_the_same_window(tmp_path):
    w = make(tmp_path)
    for screen, show in screens(w):
        show()
        w.resize(1300, 850)
        QTest.qWait(1)
        rects = L.capture(screen)
        w.resize(900, 650)              # раскладка кода ушла бы за окном
        L.apply(screen, rects)
        assert L.ai_mode(screen)
        w.resize(1300, 850)
        QTest.qWait(1)
        assert L.placed(screen) == rects, screen
    w.close()


def broken(rects, name, change):
    out = dict(rects)
    x, y, ww, hh = out[name]
    out[name] = change(x, y, ww, hh)
    return out


def test_laws_catch_overlap_outside_tiny_button_and_short_label(tmp_path):
    w = make(tmp_path)
    w.show_menu()
    m = w.menu
    rects = L.capture(m)
    assert check_layout(m, rects) == []
    play = rects["play"]
    cases = {
        "налезает": broken(rects, "stats", lambda x, y, a, b: (x, play[1] + 5, a, b)),
        "вне окна": broken(rects, "info", lambda x, y, a, b: (x, m.height() - 5, a, b)),
        "мало места": broken(rects, "play", lambda x, y, a, b: (x, y, a, 20)),
        "мало места ": broken(rects, "title", lambda x, y, a, b: (x, y, 60, b)),
        "нет места": {k: v for k, v in rects.items() if k != "subtitle"},
        "больше предела": broken(rects, "play", lambda x, y, a, b: (x - 50, y, a + 100, b)),
    }
    for want, bad_rects in cases.items():
        problems = check_layout(m, bad_rects)
        assert any(want.strip() in p for p in problems), (want, problems)
    w.play()
    ms = w.match_screen
    rects = L.capture(ms)
    small = broken(rects, "board", lambda x, y, a, b: (x, y, 200, 200))
    assert any("board: мало места" in p for p in check_layout(ms, small))
    child = broken(rects, "pause", lambda x, y, a, b: (x + 200, y, a, b))
    assert any("вне panel" in p for p in check_layout(ms, child))
    w.close()


def test_style_law_catches_unreadable_text():
    t = dict(theme.tokens("dark"))
    t["muted"] = t["bg"]
    assert any("muted" in p for p in check_style(t))


def test_back_to_code_after_ai(tmp_path):
    w = make(tmp_path)
    w.show_settings()
    s = w.settings_screen
    rects = L.capture(s)
    shifted = {k: (x + 3, y + 2, a, b) for k, (x, y, a, b) in rects.items()}
    L.apply(s, shifted)
    assert L.placed(s)["row_speed"] != rects["row_speed"]
    L.use_code(s)
    assert not L.ai_mode(s) and L.placed(s) == rects
    w.close()
