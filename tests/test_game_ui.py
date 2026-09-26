import json
import pathlib

import numpy as np
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFontInfo, QFontMetricsF, QImage, QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from game import match as M
from game import store as st
from game.app import MIN_HEIGHT, MIN_WIDTH, MainWindow
from game.board import PALETTES, Board
from game.screens import DRAW_SUBTEXT, ROUND_TEXT
from game.sound import Sounds
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, Const, FakeModels, qapp
from world.cells import DOWN, LEFT, RIGHT, UP
from world.start import start_field


@pytest.fixture
def app():
    return qapp()


@pytest.fixture
def make_window(tmp_path, app):
    made = []

    def make(models=None):
        w = MainWindow(st.Store(tmp_path / "data"), models or FakeModels(),
                       sounds=Sounds(enabled=False))
        made.append(w)
        return w
    yield make
    for w in made:
        w.close()


def rendered(widget):
    """Нарисовать виджет в картинку; пустая картинка - ошибка."""
    widget.resize(max(widget.width(), 400), max(widget.height(), 300))
    pix = widget.grab()
    assert not pix.isNull()
    return pix.toImage()


def test_every_screen_paints(make_window):
    w = make_window(FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}))
    w.resize(1040, 720)
    for show in (w.show_menu, w.show_stats, w.show_settings, w.play, w.show_menu):
        show()
        rendered(w)
    assert w.stack.currentWidget() is w.menu


def test_match_screen_paints_in_every_phase(make_window):
    w = make_window()
    w.resize(1040, 720)
    w.play()
    ms = w.match_screen
    seen = []
    for _ in range(3000):
        phase = ms.match.phase
        if not seen or seen[-1] != phase:
            seen.append(phase)
            rendered(w)                              # рисуем на каждой смене фазы
        if phase == M.MATCH_OVER:
            break
        ms.advance(60)
    seen = set(seen)
    assert seen == {M.COUNTDOWN, M.PLAYING, M.ROUND_OVER, M.MATCH_OVER}


def test_keys_reach_the_queue(make_window):
    w = make_window()
    w.play()
    ms = w.match_screen
    QTest.keyClick(ms, Qt.Key.Key_Up)
    QTest.keyClick(ms, Qt.Key.Key_A)
    QTest.keyClick(ms, Qt.Key.Key_D)                # третье нажатие - мимо очереди
    assert list(ms.match.keys) == [UP, LEFT]
    ms.match.keys.clear()
    ms.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S, Qt.KeyboardModifier.NoModifier, "s"))
    ms.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right,
                               Qt.KeyboardModifier.NoModifier))
    assert list(ms.match.keys) == [DOWN, RIGHT]


def test_russian_layout_wasd(make_window):
    w = make_window()
    w.play()
    ms = w.match_screen
    # На русской раскладке W и A дают «Ц» и «Ф».
    ms.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, 0x0426, Qt.KeyboardModifier.NoModifier, "ц"))
    ms.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, 0x0424, Qt.KeyboardModifier.NoModifier, "ф"))
    assert list(ms.match.keys) == [UP, LEFT]


def test_escape_pauses_and_goes_to_menu(make_window):
    w = make_window()
    w.play()
    ms = w.match_screen
    QTest.keyClick(ms, Qt.Key.Key_Escape)
    assert ms.match.paused and ms.overlay.isVisibleTo(ms)
    before = ms.match.count
    ms.advance(5000)
    assert ms.match.count == before
    ms.resume_button.click()
    assert not ms.match.paused and not ms.overlay.isVisibleTo(ms)
    QTest.keyClick(ms, Qt.Key.Key_Escape)
    ms.menu_button.click()
    assert w.stack.currentWidget() is w.menu
    assert ms.match is None


def play_to_end(ms, guard=5000):
    for _ in range(guard):
        if ms.match.phase == M.MATCH_OVER:
            return
        ms.advance(60)
    raise AssertionError("матч не кончился")


def test_finished_match_goes_to_stats(make_window, tmp_path):
    models = FakeModels(opponent=Const(DOWN))
    w = make_window(models)
    w.store.set("opponent", "strong")
    w.play()
    assert models.levels == ["strong"]
    play_to_end(w.match_screen)
    saved = json.loads((tmp_path / "data" / "stats.json").read_text(encoding="utf-8"))
    assert saved["matches"] == 1 and saved["rounds"] == 3
    assert saved["levels"]["strong"]["match_wins"] == 1 and saved["levels"]["strong"]["wins"] == 3
    assert saved["longest"] >= 3
    assert w.match_screen.overlay.isVisibleTo(w.match_screen)
    w.match_screen.again_button.click()
    assert w.match_screen.match.phase == M.COUNTDOWN and w.match_screen.match.score == [0, 0]


def test_missing_model_shows_message(make_window):
    w = make_window(FakeModels(missing="Нет файла models/world.npz"))
    w.play()
    assert w.stack.currentWidget() is w.menu
    assert "world.npz" in w.menu.message.text() and w.menu.message.isVisibleTo(w.menu)
    rendered(w)


def test_settings_are_saved_at_once(make_window, tmp_path):
    w = make_window()
    w.show_settings()
    s = w.settings_screen
    s.speed.setValue(200)
    s.volume.setValue(25)
    s.opponent.setCurrentIndex(2)
    s.palette.setCurrentIndex(1)
    s.food_map.setChecked(True)
    back = st.load_settings(tmp_path / "data" / "settings.json")
    assert back == {"speed_ms": 200, "opponent": "strong", "volume": 25, "palette": 1,
                    "show_food_map": True}
    assert w.match_screen.board.palette_index == 1


def test_settings_screen_shows_saved_values(tmp_path, app):
    s = st.Store(tmp_path)
    s.set("speed_ms", 90)
    s.set("opponent", "novice")
    w = MainWindow(s, FakeModels(), sounds=Sounds(enabled=False))
    w.show_settings()
    assert w.settings_screen.speed.value() == 90
    assert w.settings_screen.opponent.currentData() == "novice"
    w.close()


def test_stats_screen_with_and_without_passports(make_window):
    w = make_window()
    w.show_stats()
    assert w.stats_screen.visible_charts() == 0
    rendered(w)
    w2 = make_window(FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}))
    w2.resize(1040, 720)
    w2.show_stats()
    assert w2.stats_screen.visible_charts() == 4
    assert "99.6" in w2.stats_screen.accuracy_text()
    rendered(w2)
    w3 = make_window(FakeModels(passports={"world": {"final": "мусор", "curve": [1, None]}}))
    w3.show_stats()
    rendered(w3)


def board_image(board, size=640):
    board.resize(size, size)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)
    board.render(img)
    return img


def test_board_paints_palettes_and_food_map(app):
    b = Board()
    field = start_field()
    probs = np.zeros((32, 32))
    probs[5:10, 5:10] = 1 / 25
    images = []
    for pal in range(len(PALETTES)):
        b.set_palette(pal)
        b.set_state(field, food_probs=probs, show_food_map=False)
        images.append(board_image(b))
    assert images[0] != images[1] != images[2]
    b.set_palette(0)
    b.set_state(field, food_probs=probs, show_food_map=True, crashed=(True, False), text="3")
    assert board_image(b) != images[0]


def test_board_keeps_square_cells(app):
    b = Board()
    b.resize(900, 500)
    rect = b.field_rect()
    assert abs(rect.width() - rect.height()) < 1e-6 and rect.height() <= 500
    assert rect.center().x() == pytest.approx(450, abs=1)


# Законы из крестиков-ноликов (26.09.2026, Алексей: подсказка обрезана на его экране):
# подпись с переносом строк не ограничена по высоте и целиком помещается в окне
# минимального размера, даже если текст на 10% шире, чем в offscreen.
QWIDGETSIZE_MAX = 16777215


def wrapped_labels(widget):
    return [lb for lb in widget.findChildren(QLabel) if lb.wordWrap() and lb.isVisible() and lb.text()]


def screens(w):
    return (("меню", w.show_menu), ("статистика", w.show_stats), ("настройки", w.show_settings),
            ("матч", w.play))


def test_wrapping_labels_are_never_capped_in_height(make_window):
    w = make_window(FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}))
    w.show()
    for name, show in screens(w):
        show()
        QTest.qWait(10)
        capped = [lb.text() for lb in wrapped_labels(w) if lb.maximumHeight() < QWIDGETSIZE_MAX]
        assert capped == [], (name, capped)


@pytest.mark.parametrize("scale", [1.0, 1.1])
def test_text_fits_at_minimum_window_size(make_window, scale):
    w = make_window(FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}))
    w.show()
    w.play()                                  # все экраны созданы - шрифты правим один раз
    w.show_menu()
    for lb in w.findChildren(QLabel):
        px = lb.font().pixelSize() if lb.font().pixelSize() > 0 else round(lb.font().pointSizeF() * 96 / 72)
        lb.setStyleSheet(f"font-size: {round(px * scale)}px;")
    for name, show in screens(w):
        show()
        w.resize(w.minimumSize())
        QTest.qWait(30)
        clipped = [(lb.text()[:40], lb.height(), lb.heightForWidth(lb.width())) for lb in wrapped_labels(w)
                   if lb.heightForWidth(lb.width()) > lb.height()]
        assert clipped == [], (name, clipped)


def test_stats_show_win_rate_from_the_real_player_passport(make_window):
    """Столбец «выигрыш у бота» читает настоящий паспорт models/player.json (levels.*.vs_bot.win),
    а не выдуманный формат: в первом кадре статистики там стояли прочерки."""
    real = json.loads((pathlib.Path(__file__).resolve().parents[1] / "models" / "player.json").read_text(encoding="utf-8"))
    w = make_window(FakeModels(passports={"world": WORLD_PASSPORT, "player": real}))
    w.show_stats()
    for lv in ("novice", "medium", "strong"):
        text = w.stats_screen.level_cells[lv, "win_vs_bot"].text()
        assert text.endswith("%"), (lv, text)
        assert text == f"{round(real['levels'][lv]['vs_bot']['win'] * 100)}%"


# Замечание Алексея (26.09.2026): в конце раунда надпись о том, кто победил, слишком крупная.
# Было: шрифт 14% высоты поля, «Раунд за сетью» шире самого поля (104%). Закон: надпись на
# поле не больше 10% высоты поля и не шире 75% поля, а со шрифтом на 10% шире, чем в
# offscreen, целиком помещается в свою полосу - в обычном окне и в окне минимального размера.
CAPTIONS = [("3", "Раунд 1")] + [(t, DRAW_SUBTEXT if k == "draw" else "счёт 2 : 3")
                                 for k, t in ROUND_TEXT.items()]


@pytest.mark.parametrize("size", [(1040, 720), (MIN_WIDTH, MIN_HEIGHT)])
def test_board_caption_is_modest_and_fits(make_window, size):
    w = make_window()
    w.show()
    w.play()
    w.resize(*size)
    QTest.qWait(30)
    board = w.match_screen.board
    rect = board.field_rect()
    for text, sub in CAPTIONS:
        board.set_state(start_field(), text=text, subtext=sub)
        big, small, band, main, sub_rect = board.caption_layout(rect)
        assert QFontInfo(big).family(), "нет системных шрифтов - мерить нечего"
        fm = QFontMetricsF(big)
        width = fm.horizontalAdvance(text)
        assert big.pixelSize() <= rect.height() * 0.10, (size, text, big.pixelSize(), rect.height())
        assert width <= rect.width() * 0.75, (size, text, width, rect.width())
        assert width * 1.1 <= main.width() and fm.height() <= main.height(), (size, text)
        fs = QFontMetricsF(small)
        assert fs.horizontalAdvance(sub) * 1.1 <= sub_rect.width(), (size, sub)
        assert fs.height() <= sub_rect.height() and sub_rect.bottom() <= band.bottom() + 1, (size, sub)
        assert rect.contains(band), (size, text)
