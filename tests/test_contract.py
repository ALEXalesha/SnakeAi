"""Вход игры по контракту PythonAiGames: GAME_INFO и create_widget(ctx) без окна.

Виджет создаётся так, как его создаёт оболочка AiGameRoom: aikit.Context с папкой данных,
темой и языком; тема и язык меняются на лету; pause/resume/shutdown; файлы - только в
ctx.data_dir. Окна - только offscreen.
"""
import json
import os
import re
import subprocess
import sys
import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QMainWindow, QWidget

import game
import main
from aikit.host import Context
from game.core import match as M
from game.ui import i18n, theme
from game.ui.sound import Sounds
from game.ui.widget import GameWidget
from game.version import VERSION
from qt_app import PLAYER_PASSPORT, WORLD_PASSPORT, Const, FakeModels, qapp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYRILLIC = re.compile("[А-Яа-яЁё]")


@pytest.fixture
def app():
    return qapp()


@pytest.fixture
def ctx(tmp_path):
    return Context(tmp_path / "data", "dark", "ru", 0)


@pytest.fixture
def gw(app, ctx):
    w = GameWidget(ctx, FakeModels(passports={"world": WORLD_PASSPORT, "player": PLAYER_PASSPORT}),
                   sounds=Sounds(enabled=False))
    w.resize(1180, 780)
    w.show()
    yield w
    w.shutdown()
    w.close()


# --- GAME_INFO ---


def test_game_info_is_complete_in_both_languages():
    info = game.GAME_INFO
    assert info["id"] == "snake" and info["version"] == VERSION
    for key in ("title", "summary"):
        assert set(info[key]) == {"ru", "en"} and all(v.strip() for v in info[key].values())
    assert not CYRILLIC.search(info["title"]["en"] + info["summary"]["en"])
    assert os.path.isfile(os.path.join(ROOT, info["preview"]))


def test_version_is_the_same_in_the_game_and_the_installer():
    import build
    assert build.version() == VERSION


def test_importing_the_game_does_not_load_qt():
    """Сеть-мир, соперник и обучение работают без Qt: game/__init__ его не тянет."""
    code = ("import sys, game; import game.core.match, game.ai.world_net, game.ai.player_net, game.ai.models; "
            "print('PySide6' in sys.modules)")
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "False", r.stderr


# --- виджет ---


def test_create_widget_gives_a_plain_widget_with_real_models(app, ctx):
    w = game.create_widget(ctx)
    try:
        assert isinstance(w, QWidget) and not isinstance(w, QMainWindow)
        assert w.parent() is None and w.stack.currentWidget() is w.menu
        assert w.menu.quit_button.isHidden()           # во вкладке оболочки «Выхода» нет
        w.play()                                       # настоящие сеть-мир и соперник грузятся
        assert w.match_screen.match is not None
    finally:
        assert w.shutdown() is True
        w.close()


def test_standalone_window_shows_quit_and_it_closes_the_window(app):
    window, _ = main.open_window()
    window.show()
    assert window.game.menu.quit_button.isVisible()
    window.game.menu.quit_button.click()
    assert not window.isVisible()


def test_theme_changes_on_the_fly(gw, ctx):
    ctx.set_theme("light")
    light = theme.tokens("light", gw.style_now)      # акцентные цвета - от сети-дизайнера
    assert light["bg"] in gw.styleSheet()
    assert gw.palette().color(gw.palette().ColorRole.Highlight).name() == light["selection"]   # Fusion рисует по палитре
    assert gw.stats_screen.chart_rl.colors == theme.tokens("light")
    corner = gw.grab().toImage().pixelColor(3, gw.height() - 3)
    assert corner.name() == light["bg"]
    ctx.set_theme("dark")
    assert theme.tokens("dark")["bg"] in gw.styleSheet()
    assert gw.palette().color(gw.palette().ColorRole.Highlight).name() ==         theme.tokens("dark", gw.style_now)["selection"]


def visible_texts(widget):
    out = []
    for w in widget.findChildren(QLabel) + widget.findChildren(QAbstractButton):
        if w.isVisible() and w.text():
            out.append(w.text())
    for combo in widget.findChildren(QComboBox):
        out += [combo.itemText(i) for i in range(combo.count())]
    return out


def test_language_changes_on_the_fly_and_every_screen_is_english(gw, ctx):
    ctx.set_lang("en")
    assert gw.menu.play_button.text() == "Play"
    for show in (gw.show_menu, gw.show_stats, gw.show_settings, gw.play):
        show()
        QTest.qWait(10)
        russian = [t for t in visible_texts(gw) if CYRILLIC.search(t) and t != i18n.LANG_NAMES["ru"]]
        assert russian == [], (show.__name__, russian)
    ms = gw.match_screen
    assert ms.board.text in ("3", "2", "1") and ms.board.subtext == "Round 1"
    ms.pause()
    assert ms.overlay.title.text() == "Pause"
    ctx.set_lang("ru")                                 # карточка паузы переводится на месте
    assert ms.overlay.title.text() == "Пауза" and ms.board.subtext == "Раунд 1"


def test_both_languages_have_the_same_strings():
    assert set(i18n.RU) == set(i18n.EN)
    assert [k for k, v in i18n.EN.items() if CYRILLIC.search(v)] == []
    assert i18n.translator("en").missing() == {}


def test_settings_screen_sends_theme_language_and_volume_to_ctx(gw, ctx):
    gw.show_settings()
    s = gw.settings_screen
    s.theme_combo.setCurrentIndex(1)
    s.lang_combo.setCurrentIndex(1)
    s.volume.setValue(40)
    assert (ctx.theme, ctx.lang, ctx.sound.volume) == ("light", "en", 40)
    assert gw.sounds.volume == 40
    assert s.theme_combo.currentData() == "light" and s.lang_combo.currentData() == "en"


def test_volume_changed_by_the_host_reaches_the_game_sounds(gw, ctx):
    ctx.set_volume(55)                  # громкость оболочки меняется без сигнала
    gw.play_sound("eat")
    assert gw.sounds.volume == 55


# --- pause / resume / shutdown ---


def test_pause_stops_the_match_and_resume_restarts_the_clock(gw):
    gw.play()
    ms = gw.match_screen
    assert ms.timer.isActive()
    gw.pause()
    assert not ms.timer.isActive() and ms.match.paused and ms.overlay.isVisibleTo(ms)
    count = ms.match.count
    QTest.qWait(100)
    assert ms.match.count == count
    gw.resume()
    assert ms.timer.isActive() and ms.match.paused     # ждёт «Продолжить», как после ухода окна в фон
    ms.resume_button.click()
    assert not ms.match.paused


def test_resume_on_the_menu_starts_nothing(gw):
    gw.pause()
    gw.resume()
    assert not gw.match_screen.timer.isActive()


def test_shutdown_is_quick_and_stops_every_timer(gw):
    gw.play()
    gw.pause()                                         # вкладку скрыли, потом закрыли
    started = time.perf_counter()
    assert gw.shutdown() is True
    assert time.perf_counter() - started < 2.0
    assert [t for t in gw.findChildren(QTimer) if t.isActive()] == []
    gw.resume()                                        # после закрытия не оживает
    assert not gw.match_screen.timer.isActive()


# --- файлы только в ctx.data_dir ---


def snapshot(top):
    out = {}
    for folder, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "build", "dist")]
        for name in files:
            path = os.path.join(folder, name)
            out[path] = os.path.getmtime(path)
    return out


def test_game_writes_only_into_ctx_data_dir(app, ctx, tmp_path):
    before = snapshot(ROOT)
    temp_before = set(os.listdir(os.environ.get("TEMP", str(tmp_path))))
    w = GameWidget(ctx, FakeModels(opponent=Const(1)))
    w.play()
    ms = w.match_screen
    for _ in range(5000):
        if ms.match.phase == M.MATCH_OVER:
            break
        ms.advance(60)
    ctx.set_theme("light")
    ctx.set_lang("en")
    w.shutdown()
    w.close()
    after = snapshot(ROOT)
    assert sorted(p for p, m in after.items() if before.get(p) != m) == []
    assert {"settings.json", "stats.json"} <= set(os.listdir(ctx.data_dir)) or \
        "stats.json" in os.listdir(ctx.data_dir)
    stats = json.loads(open(os.path.join(ctx.data_dir, "stats.json"), encoding="utf-8").read())
    assert stats["matches"] == 1
    new_temp = set(os.listdir(os.environ.get("TEMP", str(tmp_path)))) - temp_before
    assert not [n for n in new_temp if n.startswith("snakeai-sounds-")]


# --- перенос данных 1.0.x в окне отдельного запуска ---


def test_data_of_1_0_is_copied_into_the_contract_layout(tmp_path):
    old, root = tmp_path / "old", tmp_path / "root"
    old.mkdir()
    (old / "settings.json").write_text(json.dumps({"speed_ms": 90, "volume": 25, "palette": 2}), encoding="utf-8")
    (old / "stats.json").write_text(json.dumps({"matches": 4, "rounds": 11}), encoding="utf-8")
    (old / "window.json").write_text(json.dumps({"x": 1, "y": 2, "width": 900, "height": 650}), encoding="utf-8")
    done = main.migrate(str(old), str(root), str(root / "snake"))
    assert sorted(done) == ["host.json", "settings.json", "stats.json", "window.json"]
    assert json.loads((root / "host.json").read_text(encoding="utf-8"))["volume"] == 25
    assert json.loads((root / "snake" / "stats.json").read_text(encoding="utf-8"))["matches"] == 4
    assert (old / "settings.json").exists() and (old / "stats.json").exists()      # копия, не перенос
    (root / "snake" / "stats.json").write_text("{}", encoding="utf-8")
    assert main.migrate(str(old), str(root), str(root / "snake")) == []
    assert (root / "snake" / "stats.json").read_text(encoding="utf-8") == "{}"


def test_old_data_dir_is_where_1_0_kept_it(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path / "lad")}
    assert main.old_data_dir(False, "python.exe", env) == str(tmp_path / "lad" / "SnakeAIGame")
    exe = tmp_path / "app" / "SnakeAIGame.exe"
    exe.parent.mkdir()
    (exe.parent / "portable.txt").write_text("x", encoding="utf-8")
    assert main.old_data_dir(True, str(exe), env) == str(exe.parent / "saves")


def test_standalone_window_reads_settings_and_stats_of_1_0(app, tmp_path):
    old = tmp_path / "localappdata" / "SnakeAIGame"          # LOCALAPPDATA подменён в conftest
    old.mkdir(parents=True)
    (old / "settings.json").write_text(json.dumps({"speed_ms": 150, "volume": 30}), encoding="utf-8")
    (old / "stats.json").write_text(json.dumps({"matches": 9, "longest": 40}), encoding="utf-8")
    window, ctx = main.open_window()
    assert window.game.store.settings["speed_ms"] == 150 and ctx.sound.volume == 30
    assert window.game.store.stats["matches"] == 9
    assert window.minimumWidth() == 820 and window.minimumHeight() <= 690     # влезает в экран 1024x768
    window.close()
