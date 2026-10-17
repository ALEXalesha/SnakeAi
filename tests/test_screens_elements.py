"""Экраны для сети-дизайнера: список элементов, ручки отступов, настройки на всё окно."""
import numpy as np
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest

from aikit.host import Context
from game.design.knobs import knobs
from game.ui.sound import Sounds
from game.ui.widget import GameWidget
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, FakeModels, qapp


@pytest.fixture
def gw(tmp_path):
    qapp()
    w = GameWidget(Context(tmp_path / "data", "dark", "ru", 60),
                   FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}),
                   sounds=Sounds(enabled=False), design=False)
    w.resize(1040, 720)
    w.show()
    yield w
    w.close()


def shows(w):
    return ((w.menu, w.show_menu), (w.match_screen, w.play), (w.stats_screen, w.show_stats),
            (w.settings_screen, w.show_settings))


def test_elements_are_real_children(gw):
    for screen, _ in shows(gw):
        names = {}
        for name, widget, parent in screen.elements():
            assert name not in names, name
            if parent is None:
                assert screen.isAncestorOf(widget), name
            else:
                assert parent in names, (name, parent)              # родитель раньше
                assert names[parent].isAncestorOf(widget), (name, parent)
            names[name] = widget
        assert names, screen


def rect_in(screen, widget):
    p = widget.mapTo(screen, QPoint(0, 0))
    return p.x(), p.y(), widget.width(), widget.height()


@pytest.mark.parametrize("size", [(1040, 720), (1600, 1000), (820, 600)])
def test_settings_fill_the_window(gw, size):
    """Алексей: в 1.1 настройки были прижаты в левый верхний угол. Теперь карточки занимают
    всё окно под заголовком - как прокрутка статистики."""
    gw.resize(*size)
    gw.show_stats()
    QTest.qWait(10)
    sx, sy, sw, sh = rect_in(gw.stats_screen, gw.stats_screen.scroll)
    gw.show_settings()
    QTest.qWait(10)
    s = gw.settings_screen
    gx, gy, gw_, gh = rect_in(s, s.card_game)
    vx, vy, vw, vh = rect_in(s, s.card_view)
    assert gx == sx and vx + vw == sx + sw, (size, (gx, vx + vw), (sx, sx + sw))
    assert abs(gw_ - vw) <= 1 and gy == vy and gh == vh
    assert gy + gh >= s.height() - 30, (size, gy + gh, s.height())
    assert gh >= s.height() * 0.6


def test_knobs_change_margins_and_zero_restores(gw):
    gw.show_settings()
    s = gw.settings_screen
    QTest.qWait(10)
    before = rect_in(s, s.card_game), rect_in(s, s.row_opponent)
    s.set_knobs(knobs(np.array([1.0, 1.0, 0.0, 0.0])))
    s.layout().activate()
    QTest.qWait(10)
    wide = rect_in(s, s.card_game), rect_in(s, s.row_opponent)
    assert wide[0][0] > before[0][0]                         # поле экрана больше
    assert wide[1][1] - wide[0][1] > before[1][1] - before[0][1]   # промежутки больше
    s.set_knobs(knobs(np.zeros(4)))
    s.layout().activate()
    QTest.qWait(10)
    assert (rect_in(s, s.card_game), rect_in(s, s.row_opponent)) == before


def test_match_panel_blocks_in_order(gw):
    gw.play()
    QTest.qWait(10)
    ms = gw.match_screen
    blocks = [w for name, w, parent in ms.elements() if parent == "panel"]
    ys = [rect_in(ms, b)[1] for b in blocks]
    assert ys == sorted(ys) and len(set(ys)) == len(ys)
    assert all(b.isVisible() and b.height() > 0 for b in blocks)


def test_menu_flags_follow_visibility(gw):
    gw.show_menu()
    assert gw.menu.flags() == (0, 0)
    gw.allow_quit(lambda: None)
    gw.menu.show_message("ошибка")
    assert gw.menu.flags() == (1, 1)
