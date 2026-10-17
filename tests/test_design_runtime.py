"""Окно раскладывает сеть-дизайнер, клетки рисует сеть-художник; законы, пересэмплирование,
запасной код и журнал - на настоящих обученных моделях game/models."""
import pathlib
import re

import numpy as np
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from aikit.host import Context
from game.ai.models import load_designer, load_painter
from game.design import layout as L
from game.design.journal import Journal
from game.design.knobs import knobs
from game.design.laws import check_layout
from game.design.runtime import AiDesign
from game.design.tiles import CodeTiles, code_tiles, common_keys
from game.ui.sound import Sounds
from game.ui.widget import MIN_HEIGHT, MIN_WIDTH, GameWidget
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, FakeModels, qapp

ROOT = pathlib.Path(__file__).resolve().parents[1]
PASSPORTS = {"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}


@pytest.fixture
def made(tmp_path):
    qapp()
    out = []

    def make(design=None, models=None, lang="ru", size=(1040, 720)):
        w = GameWidget(Context(tmp_path / f"data{len(out)}", "dark", lang, 0),
                       models or FakeModels(passports=PASSPORTS), sounds=Sounds(enabled=False), design=design)
        w.resize(*size)
        w.show()
        out.append(w)
        return w
    yield make
    for w in out:
        w.shutdown()
        w.close()


def shows(w):
    return ((w.menu, w.show_menu), (w.match_screen, w.play), (w.stats_screen, w.show_stats),
            (w.settings_screen, w.show_settings))


def design(seed, designer=None, painter=None, journal=None):
    return AiDesign(designer if designer is not None else load_designer(),
                    painter if painter is not None else load_painter(),
                    journal or Journal(), rng=np.random.default_rng(seed))


def test_window_is_laid_out_by_the_net(made):
    w = made(design=design(0))
    for screen, show in shows(w):
        show()
        QTest.qWait(5)
        assert w.design.last[screen.NAME]["source"] == "net", (screen.NAME, w.design.last[screen.NAME])
        assert L.ai_mode(screen)
        assert check_layout(screen, L.placed(screen)) == []
    assert w.journal.data["layouts"] >= 4 and w.journal.data["layout_fallbacks"] == 0


@pytest.mark.parametrize("size", [(1040, 720), (820, 600), (1920, 1080)])
def test_net_layout_is_the_rule_and_code_the_exception(made, size):
    """На 16 запусках (разный шум) запасной вариант - не больше чем у 1 экрана из 8."""
    fallbacks = total = 0
    for seed in range(16):
        w = made(design=design(100 + seed), lang=("ru", "en")[seed % 2], size=size)
        for screen, show in shows(w):
            show()
            total += 1
            fallbacks += w.design.last[screen.NAME]["source"] != "net"
            assert check_layout(screen, L.placed(screen)) == []
        w.shutdown()
        w.close()
    assert fallbacks / total <= 1 / 8, (size, fallbacks, total)


class Garbage:
    """Сеть-дизайнер, которая выдаёт мусор (или сначала мусор, потом раскладку кода)."""

    def __init__(self, screens=None, bad_first=None):
        self.calls = 0
        self.screens = screens
        self.bad_first = bad_first

    def layout(self, screen, w, h, theme, lang, flags, z):
        self.calls += 1
        if self.bad_first is not None and self.calls > self.bad_first:
            sc = self.screens[screen]
            sc.set_knobs(knobs(z))
            return L.capture(sc)
        return {name: (0, 0, 5, 5) for name in ("logo", "title", "play", "board", "panel", "scroll")}

    def style(self, theme, lang, z):
        white = "#ffffff"
        return {"font": 1.0, "radius": 10.0, "colors": {"accent": white, "accent_hover": white,
                                                        "accent_pressed": white, "title": "#000000",
                                                        "selection": white}}


def test_bad_net_falls_back_to_code_and_is_logged(made):
    j = Journal()
    w = made(design=AiDesign(Garbage(), None, j, rng=np.random.default_rng(1)))
    w.show_menu()
    QTest.qWait(5)
    assert not L.ai_mode(w.menu) and w.design.last["menu"]["source"] == "code"
    assert check_layout(w.menu, L.placed(w.menu)) == []
    assert j.data["layout_fallbacks"] >= 1 and j.data["layout_resamples"] >= 3
    assert any(e["what"].startswith("окно: menu") for e in j.data["last"])
    assert any(e["what"] == "окно: стиль" for e in j.data["last"])      # белый акцент без контраста


def test_resample_before_fallback(made):
    j = Journal()
    net = Garbage(bad_first=1)
    w = made(design=AiDesign(net, None, j, rng=np.random.default_rng(2)))
    net.screens = {s.NAME: s for s in w.screens}
    net.calls = 0
    w.design._cache.clear()
    w.resize(1100, 760)
    w.show_settings()
    QTest.qWait(5)
    assert j.data["layout_resamples"] >= 1
    assert w.design.last["settings"]["source"] == "net"


def test_missing_models_play_on_code(made):
    w = made(models=FakeModels(passports=PASSPORTS, design_missing=True))
    assert w.design.designer is None and isinstance(w.design.tiles, CodeTiles)
    assert sum("нет сети" in e["what"] for e in w.journal.data["last"]) == 2
    for screen, show in shows(w):
        show()
        assert not L.ai_mode(screen)
    assert w.match_screen.match is not None


def test_language_theme_and_message_relayout(made):
    w = made()
    w.show_menu()
    w.ctx.set_lang("en")
    QTest.qWait(5)
    assert w.menu.play_button.text() == "Play"
    assert check_layout(w.menu, L.placed(w.menu)) == []
    w.menu.show_message("Could not load the model: something went wrong")
    QTest.qWait(5)
    assert w.menu.message.isVisible()
    assert check_layout(w.menu, L.placed(w.menu)) == []
    w.ctx.set_theme("light")
    w.show_settings()
    QTest.qWait(5)
    assert check_layout(w.settings_screen, L.placed(w.settings_screen)) == []


def wrapped(widget):
    return [lb for lb in widget.findChildren(QLabel) if lb.wordWrap() and lb.isVisible() and lb.text()]


def test_wider_fonts_on_real_screen_still_fit(made):
    """На экране Алексея текст шире, чем в offscreen: метка просит лишнюю строку. Законы
    должны это увидеть и взять раскладку кода, а не обрезать текст."""
    w = made()
    w.play()
    w.show_menu()
    for lb in w.findChildren(QLabel):
        px = lb.font().pixelSize() if lb.font().pixelSize() > 0 else round(lb.font().pointSizeF() * 96 / 72)
        lb.setStyleSheet(f"font-size: {round(px * 1.1)}px;")
    for screen, show in shows(w):
        show()
        w.resize(MIN_WIDTH, MIN_HEIGHT)
        QTest.qWait(10)
        # сеть - только если её раскладка прошла законы; иначе код (Qt сам ужимает до 2 px)
        assert w.design.last[screen.NAME]["source"] == "code" or check_layout(screen, L.placed(screen)) == []
        clipped = [lb.text()[:30] for lb in wrapped(screen) if lb.heightForWidth(lb.width()) > lb.height()]
        assert clipped == [], (screen.NAME, clipped)


@pytest.mark.parametrize("size", [(3840, 2160), (MIN_WIDTH, MIN_HEIGHT), (2560, 1440)])
def test_any_window_size_obeys_the_laws(made, size):
    w = made(size=size)
    for screen, show in shows(w):
        show()
        QTest.qWait(5)
        assert check_layout(screen, L.placed(screen)) == [], (size, screen.NAME)


def test_two_launches_differ_and_both_obey_laws(made):
    a, b = made(design=design(11)), made(design=design(12))
    diffs = []
    for (sa, show_a), (sb, show_b) in zip(shows(a), shows(b)):
        show_a()
        show_b()
        QTest.qWait(5)
        pa, pb = L.placed(sa), L.placed(sb)
        assert check_layout(sa, pa) == [] and check_layout(sb, pb) == []
        diffs += [np.abs(np.subtract(pa[n], pb[n])).mean() for n in pa if n in pb]
    assert np.mean(diffs) > 2, np.mean(diffs)
    assert a.style_now["colors"]["accent"] != b.style_now["colors"]["accent"]


def test_board_tiles_come_from_the_painter(made):
    w = made()
    w.play()
    tiles = w.match_screen.board.tiles
    w.match_screen.board.cells_image()
    assert tiles.code.get(0) is False and w.journal.data["tile_sets"] >= 1
    keys = common_keys()[:20]
    net = np.stack([tiles.tiles(0, keys)[int(k)] for k in keys])
    code = code_tiles(keys, 0, tiles._z_of[0])
    assert not np.array_equal(net, code)                     # рисует сеть, не код
    assert np.abs(net.astype(int) - code).mean() / 255 <= tiles.limit
    v = tiles.version
    w.play()
    assert tiles.version == v + 1                           # новая партия - новая рука


class BadPainter:
    def draw(self, keys, palette, z):
        return np.zeros((len(keys), 24, 24, 3), np.uint8)


def test_bad_painter_falls_back_to_code_tiles(made):
    j = Journal()
    w = made(design=AiDesign(load_designer(), BadPainter(), j, rng=np.random.default_rng(3)))
    w.play()
    img = w.match_screen.board.cells_image()
    assert img.mean() > 5
    assert j.data["tile_fallbacks"] == 1 and j.data["tile_resamples"] == 3
    assert w.match_screen.board.tiles.code[0] is True


def test_runtime_does_not_import_teacher_or_train():
    pat = re.compile(r"^\s*(from|import)\s+game\.(teacher|train)\b", re.M)
    files = sorted((ROOT / "game" / "design").rglob("*.py")) + sorted((ROOT / "game" / "ui").rglob("*.py"))
    assert len(files) > 10
    for path in files:
        assert not pat.search(path.read_text(encoding="utf-8")), path


def test_language_switch_lays_out_the_new_texts(made):
    """Смена языка: раскладка считается уже по новым текстам. Было (самопроверка 17.10):
    дизайнер получал язык раньше текстов, законы видели «Настройки» в месте под «Settings», и
    экран навсегда уходил в запасной вариант."""
    w = made(design=design(6))
    for lang in ("en", "ru", "en"):
        w.ctx.set_lang(lang)
        for screen, show in shows(w):
            show()
            assert w.design.last[screen.NAME]["source"] == "net", (lang, screen.NAME, w.design.last[screen.NAME])
    assert w.journal.data["layout_fallbacks"] == 0


def test_transient_small_pages_are_not_judged(made):
    """Страница стопки до первой раскладки окна - 640x480, меньше окна игры: её не судят и не
    пишут в журнал (самопроверка 17.10 считала это запасным вариантом)."""
    from game.design.runtime import MIN_SIZE
    assert MIN_SIZE == (MIN_WIDTH, MIN_HEIGHT)
    w = made(design=design(4))
    w.match_screen.resize(640, 480)
    w.design.layout(w.match_screen)
    assert not L.ai_mode(w.match_screen) and w.journal.data["layout_fallbacks"] == 0


def test_journal_survives_garbage_and_restarts(tmp_path):
    (tmp_path / "ai_ui.json").write_text('{"layouts": "много", "last": [1, {"what": "x", "why": "y"}]}',
                                        encoding="utf-8")
    j = Journal(tmp_path)
    assert j.data["layouts"] == 0 and j.data["last"] == [{"what": "x", "why": "y"}]
    j.count("layouts", 3)
    j.deviation(2.0)
    j.note("окно: menu", "проверка")
    again = Journal(tmp_path)
    assert again.data["layouts"] == 3 and again.mean_deviation() == 2.0
    assert again.data["last"][-1]["why"] == "проверка"
