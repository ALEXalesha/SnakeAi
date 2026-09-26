"""Нейро-змейка: запуск окна. Поле двигает сеть-мир, кода правил в игре нет.

    python main.py                      # игра
    python main.py --selftest итог.txt  # самопроверка без экрана: матч настоящих сетей
"""
import argparse
import os
import sys
import time


def selftest(out_path, max_steps=1500):
    """Без экрана: настоящая сеть-мир и соперник «сильный» против «среднего» за игрока,
    несколько раундов; окно создаётся и рисуется. Итог - в файл, код 0 - всё работает."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import tempfile

    import numpy as np
    from PySide6.QtWidgets import QApplication

    from game import app, match, models, store
    from game.sound import Sounds
    from world.cells import chain

    lines = ["Нейро-змейка, самопроверка", f"собранная версия: {'да' if getattr(sys, 'frozen', False) else 'нет'}"]
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

    win = app.MainWindow(store.Store(tempfile.mkdtemp()), m, sounds=Sounds(enabled=False))
    win.resize(1040, 720)
    win.show()
    for show in (win.show_menu, win.show_stats, win.show_settings):
        show()
        ok = ok and not win.grab().isNull()
    win.close()
    lines.append("окно: меню, статистика, настройки нарисованы")
    lines.append("ИТОГ: " + ("работает" if ok else "СБОЙ"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Нейро-змейка")
    ap.add_argument("--selftest", metavar="ФАЙЛ", nargs="?", const="selftest.txt",
                    help="самопроверка без экрана, итог в файл")
    args = ap.parse_args()
    if args.selftest:
        return selftest(args.selftest)

    from PySide6.QtWidgets import QApplication

    from game import app, models, paths, store, theme

    if sys.platform == "win32":
        try:   # свой значок на панели задач, а не значок python.exe
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SnakeAIGame")
        except (OSError, AttributeError):
            pass
    qt = QApplication(sys.argv)
    qt.setApplicationName("SnakeAIGame")
    qt.setApplicationDisplayName("Нейро-змейка")
    theme.apply(qt)
    data = paths.data_dir()
    return app.run(store.Store(data), models.Models(), os.path.join(data, "window.json"))


if __name__ == "__main__":
    sys.exit(main())
