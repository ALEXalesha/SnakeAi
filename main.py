"""Нейро-змейка: запуск окна. Поле двигает сеть-мир, кода правил в игре нет.

    python main.py                      # игра
    python main.py --offscreen          # без экрана (проверки)
    python main.py --selftest итог.txt  # самопроверка без экрана: матч настоящих сетей

Игра - виджет по контракту PythonAiGames (game/__init__.py); здесь только окно отдельного
запуска (aikit.make_window) с размером и «Выходом», как до 1.1.0, и перенос данных 1.0.x.
"""
import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APP_NAME = "SnakeAIGame"
HOME_ENV = "SNAKEAIGAME_HOME"            # подменяет папку данных целиком (тесты, самопроверка)
# окно - как у 1.0.x: 1040x720, не меньше 820x600
WINDOW_OPTS = {"width": 1040, "height": 720, "minWidth": 820, "minHeight": 600}


def old_data_dir(frozen, exe, env):
    """Где 1.0.x держал настройки и статистику: %LOCALAPPDATA%\\SnakeAIGame, у portable - saves
    рядом с exe."""
    if frozen:
        beside = os.path.dirname(os.path.abspath(exe))
        if os.path.exists(os.path.join(beside, "portable.txt")):
            return os.path.join(beside, "saves")
    base = env.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def migrate(old, root, game_dir):
    """Перенести данные 1.0.x в раскладку контракта: settings.json и stats.json - в папку игры,
    window.json - в корень, громкость - в host.json. Копией: старые файлы остаются на месте,
    уже перенесённое не перезаписывается. Возвращает список перенесённого."""
    from aikit import host, settings
    from aikit.storage import load_json

    done = []
    for name, folder in (("settings.json", game_dir), ("stats.json", game_dir), ("window.json", root)):
        src, dst = os.path.join(old, name), os.path.join(folder, name)
        if os.path.isfile(src) and not os.path.exists(dst) and os.path.abspath(src) != os.path.abspath(dst):
            os.makedirs(folder, exist_ok=True)
            shutil.copy2(src, dst)
            done.append(name)
    host_path = os.path.join(root, "host.json")
    old_settings = load_json(os.path.join(old, "settings.json"))
    if not os.path.exists(host_path) and isinstance(old_settings, dict):
        hs = settings.Settings(host.host_schema(), host_path)
        try:
            hs.set("volume", old_settings["volume"])
        except (KeyError, ValueError):
            pass
        hs.save()
        done.append("host.json")
    return done


def open_window(root=None, migrate_old=True):
    """Окно отдельного запуска с виджетом игры. QApplication должно уже быть. Возвращает
    (окно, ctx); окно ещё не показано - window.memory.show(). migrate_old=False - не искать
    данные 1.0.x (самопроверка не трогает профиль игрока)."""
    import aikit
    from aikit.window_state import WindowMemory
    from game import GAME_INFO, create_widget
    from game.ui import theme
    from game.ui.widget import make_icon

    root = root or aikit.data_root(APP_NAME)
    if migrate_old:
        migrate(old_data_dir(aikit.frozen(), sys.executable, os.environ), root, os.path.join(root, GAME_INFO["id"]))
    window, ctx = aikit.make_window(GAME_INFO, create_widget, APP_NAME, root)
    need = window.game.minimumSizeHint()
    opts = {**WINDOW_OPTS, "minWidth": max(WINDOW_OPTS["minWidth"], need.width()),
            "minHeight": max(WINDOW_OPTS["minHeight"], need.height())}
    window.window_opts = opts
    window.setMinimumSize(opts["minWidth"], opts["minHeight"])
    window.memory = WindowMemory(window, os.path.join(root, "window.json"), opts)
    window.setWindowIcon(make_icon())
    window.game.allow_quit(window.close)
    # вид - как в 1.0: стиль Fusion и палитра приложения, а таблица стилей окна aikit не
    # нужна (у виджета своя, и общая просачивалась бы в него: фон стопки экранов, стрелка
    # выпадающих списков). Окно aikit по ctx.changed ставит её снова - вместо этого только
    # заголовок. В оболочке ничего этого нет: там виджет сам ставит себе палитру и стили.
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    ctx.changed.disconnect(window.apply)
    window.setStyleSheet("")

    def restyle(*_):
        title = GAME_INFO["title"].get(ctx.lang, GAME_INFO["title"]["en"])
        window.setWindowTitle(f"{title} {GAME_INFO['version']}")
        theme.apply(app, ctx.theme)
    restyle()
    ctx.changed.connect(restyle)
    return window, ctx


def selftest(out_path, max_steps=1500):
    """Без экрана: настоящая сеть-мир и соперник «сильный» против «среднего» за игрока,
    несколько раундов; окно создаётся и рисуется. Итог - в файл, код 0 - всё работает."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import tempfile

    import numpy as np
    from PySide6.QtWidgets import QApplication

    from aikit import offscreen
    offscreen.setup(force=True)
    os.environ[HOME_ENV] = tempfile.mkdtemp(prefix="snakeai-selftest-")
    from game.ai import models
    from game.core import match
    from game.core.cells import chain
    from game.version import VERSION

    lines = [f"Нейро-змейка {VERSION}, самопроверка",
             f"собранная версия: {'да' if getattr(sys, 'frozen', False) else 'нет'}"]
    ok = True
    qt = QApplication.instance() or QApplication([])  # noqa: F841
    m = models.Models()
    world, net, player = m.load_world(), m.load_opponent("strong"), m.load_opponent("medium")
    t0 = time.time()
    game = match.Match(world, net, np.random.default_rng(1), target=3)
    steps = broken = 0
    confidence = []
    while game.phase != match.MATCH_OVER and steps < max_steps:
        if game.phase == match.PLAYING:
            game.press(player.act(game.field, 0))
            game.step()
            steps += 1
            if game.confidence is not None:
                confidence.append(game.confidence)
            if game.phase == match.PLAYING and (chain(game.field, 0) is None or chain(game.field, 1) is None):
                broken += 1
        else:
            game.update(2000)
    per_move = (time.time() - t0) / max(steps, 1) * 1000
    lines.append(f"матч: счёт {game.score[0]}:{game.score[1]}, раундов {game.round}, ходов {steps}, "
                 f"{per_move:.1f} мс на ход")
    lines.append(f"уверенность сети-мира: средняя {np.mean(confidence):.3f}, наименьшая {np.min(confidence):.3f}")
    lines.append(f"змейки порваны: {broken} раз")
    ok = ok and steps > 50 and broken == 0

    win, ctx = open_window(migrate_old=False)
    win.resize(1040, 720)
    win.show()
    gw = win.game
    for lang in ("ru", "en"):
        ctx.set_lang(lang)
        for show in (gw.show_menu, gw.show_stats, gw.show_settings):
            show()
            ok = ok and not win.grab().isNull()
    ok = ok and gw.shutdown() is True
    win.close()
    lines.append("окно: меню, статистика, настройки нарисованы по-русски и по-английски")
    lines.append("ИТОГ: " + ("работает" if ok else "СБОЙ"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Нейро-змейка")
    ap.add_argument("--selftest", metavar="ФАЙЛ", nargs="?", const="selftest.txt",
                    help="самопроверка без экрана, итог в файл")
    ap.add_argument("--offscreen", action="store_true", help="без экрана")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest(args.selftest)
    if args.offscreen:
        from aikit import offscreen
        offscreen.setup(force=True)

    from PySide6.QtWidgets import QApplication

    if sys.platform == "win32":
        try:   # свой значок на панели задач, а не значок python.exe
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SnakeAIGame")
        except (OSError, AttributeError):
            pass
    qt = QApplication.instance() or QApplication(sys.argv)
    qt.setApplicationName(APP_NAME)
    window, _ = open_window()
    window.memory.show()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
