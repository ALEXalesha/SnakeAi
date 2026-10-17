"""Свой вид змейки «террариум» (2.1) и находки проверки 17.10: меню, настройки и статистика в
стиле игры, флажок видно, на 4K не крошечно, брошенный матч - поражение."""
import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from aikit.host import Context
from aikit.skin import DEFAULT, page_problems
from game.core import match as M
from game.core.cells import DOWN
from game.ui import theme
from game.ui.look import SKIN, scale_for
from game.ui.sound import Sounds
from game.ui.widget import GameWidget
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, Const, FakeModels, qapp


@pytest.fixture
def make(tmp_path):
    qapp()
    made = []

    def build(models=None, design=False, theme_name="dark", lang="ru"):
        w = GameWidget(Context(tmp_path / "data", theme_name, lang, 0),
                       models or FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}),
                       sounds=Sounds(enabled=False), design=design)
        w.resize(1040, 720)
        w.show()
        made.append(w)
        return w
    yield build
    for w in made:
        w.shutdown()
        w.close()


def pump(n=4):
    for _ in range(n):
        QApplication.processEvents()


def mean(img):
    r = g = b = 0
    n = 0
    for y in range(0, img.height(), 2):
        for x in range(0, img.width(), 2):
            c = img.pixelColor(x, y)
            r, g, b, n = r + c.red(), g + c.green(), b + c.blue(), n + 1
    return r / n, g / n, b / n


@pytest.mark.parametrize("theme_name", theme.THEMES)
def test_food_map_checkbox_shows_its_state(make, theme_name):
    """Проверка 17.10: «Показывать на поле» выглядел одинаково включённым и выключенным."""
    w = make(theme_name=theme_name)
    w.show_settings()
    box = w.settings_screen.food_map
    pump()
    box.setChecked(False)
    off = mean(box.grab().toImage())
    box.setChecked(True)
    on = mean(box.grab().toImage())
    assert max(abs(a - b) for a, b in zip(on, off)) > 12, (on, off)


def test_scale_steps():
    assert scale_for(820, 600) == scale_for(1040, 720) == scale_for(1366, 728) == 1.0
    assert scale_for(1920, 1040) == 1.45 and scale_for(1100, 760) == 1.05
    assert scale_for(3840, 2120) == scale_for(9000, 9000) == 2.0


def test_4k_window_is_not_tiny(make):
    """Проверка 17.10: на 3840x2120 без масштаба Windows меню и панель матча были крошечными."""
    w = make()
    w.show_menu()
    pump()
    small = (w.menu.play_button.height(), w.menu.title_label.fontMetrics().height(),
             w.match_screen.panel.width())
    w.resize(3840, 2120)
    pump()
    assert w.scale == 2.0
    big = (w.menu.play_button.height(), w.menu.title_label.fontMetrics().height(),
           w.match_screen.panel.width())
    assert all(b >= 1.8 * s for b, s in zip(big, small)), (small, big)
    w.resize(1040, 720)
    pump()
    assert w.scale == 1.0 and w.match_screen.panel.width() == small[2]


def test_menu_has_living_terrarium_only_on_screen(make):
    w = make()
    w.show_menu()
    pump()
    bd = w.menu.backdrop
    assert bd.running()
    w.pause()
    assert not bd.running()
    w.resume()
    assert bd.running()
    w.show_stats()
    pump()
    assert not bd.running()                      # меню ушло с экрана - фон не тикает
    w.show_menu()
    pump()
    assert bd.running()


def test_terrarium_differs_from_plain_look(make):
    """Страницы змейки не общим видом: фон - клетки террариума, не ровная заливка темы."""
    w = make()
    w.show_settings()
    pump()
    img = w.grab().toImage()
    bg = QColor(theme.TOKENS["dark"]["bg"])
    corner = [img.pixelColor(img.width() - 1 - x, img.height() - 1 - y) for x in range(0, 60, 3) for y in range(0, 60, 3)]
    assert any(c != bg for c in corner)
    assert w.settings_screen.TERRARIUM and w.settings_screen._backdrop is not None   # фон нарисован экраном
    assert SKIN.signature() != DEFAULT.signature()
    assert SKIN.palette("dark")["accent"] == theme.TOKENS["dark"]["accent"]
    plain = QColor(DEFAULT.palette("dark")["bg"])
    assert img.pixelColor(2, 2) != plain


@pytest.mark.parametrize("size", [(820, 600), (1040, 720), (1920, 1040), (3840, 2120)])
@pytest.mark.parametrize("lang", ["ru", "en"])
def test_stats_and_settings_pages_clean(make, size, lang):
    """aikit.skin.page_problems: ничего не обрезано, не за краем, подписи с переносом без потолка."""
    w = make(lang=lang)
    w.resize(*size)
    for show, screen in ((w.show_stats, w.stats_screen), (w.show_settings, w.settings_screen)):
        show()
        pump()
        problems = [p for p in page_problems(screen) if "QComboBox" not in p]
        assert problems == [], (size, lang, problems[:5])


def test_title_is_drawn_in_snake_skin(make):
    w = make()
    w.show_menu()
    pump()
    title = w.menu.title_label
    assert title.font().family() == "Candara"
    img = title.grab().toImage()
    colors = {img.pixelColor(x, img.height() // 2).name() for x in range(0, img.width(), 3)}
    assert len(colors) > 6                       # градиент кожи, а не одноцветная метка


def play_rounds(ms, n):
    for _ in range(20000):
        if ms.rounds_done >= n or ms.match.phase == M.MATCH_OVER:
            return
        ms.advance(60)
    raise AssertionError("раунды не сыграны")


def test_abandoned_match_counts_as_a_loss(make, tmp_path):
    """Проверка 17.10: брошенный матч - раунды записаны, а матч нет («1 матч, 4 раунда» при 0:3).
    Теперь как в КНБ 1.0.4: брошенный после сыгранного раунда - поражение матча."""
    w = make(FakeModels(opponent=Const(DOWN)))
    w.store.set("opponent", "strong")
    w.play()
    ms = w.match_screen
    play_rounds(ms, 1)
    assert ms.rounds_done == 1 and ms.match.phase != M.MATCH_OVER
    QTest.keyClick(ms, Qt.Key.Key_Escape)
    assert w.t("leave_is_loss") in ms.overlay.text.text()
    ms.menu_button.click()
    saved = json.loads((tmp_path / "data" / "stats.json").read_text(encoding="utf-8"))
    assert saved["matches"] == 1 and saved["levels"]["strong"]["match_losses"] == 1


def test_match_left_before_first_round_is_not_counted(make, tmp_path):
    w = make()
    w.play()
    ms = w.match_screen
    QTest.keyClick(ms, Qt.Key.Key_Escape)
    assert w.t("leave_is_loss") not in ms.overlay.text.text()
    ms.menu_button.click()
    assert w.store.stats["matches"] == 0


def test_closing_window_mid_match_is_a_loss(make):
    w = make(FakeModels(opponent=Const(DOWN)))
    w.play()
    play_rounds(w.match_screen, 1)
    w.shutdown()
    assert w.store.stats["matches"] == 1
    assert sum(lv["match_losses"] for lv in w.store.stats["levels"].values()) == 1


def test_finished_match_is_not_counted_twice(make):
    w = make(FakeModels(opponent=Const(DOWN)))
    w.play()
    ms = w.match_screen
    for _ in range(20000):
        if ms.match.phase == M.MATCH_OVER:
            break
        ms.advance(60)
    ms.menu_button.click()
    assert w.store.stats["matches"] == 1


def test_labels_with_wrap_have_no_height_cap(make):
    w = make()
    for show in (w.show_menu, w.show_stats, w.show_settings, w.play):
        show()
        pump()
    for lb in w.findChildren(QLabel):
        if lb.wordWrap():
            assert lb.maximumHeight() == 16777215, lb.objectName()


def test_checkbox_indicator_is_styled():
    for name in theme.THEMES:
        q = theme.qss(name)
        assert "QCheckBox::indicator:checked" in q and theme.TOKENS[name]["accent"] in q


def test_qss_scales_fonts_and_padding():
    a, b = theme.qss("dark"), theme.qss("dark", scale=2.0)
    assert "padding: 10px 18px" in a and "padding: 20px 36px" in b
