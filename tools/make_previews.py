"""Картинки для README: экраны окна без показа на экране (Qt offscreen).

    python tools/make_previews.py [--models models] [--out docs]

Матч играется настоящими сетями: мир - сеть-мир, соперник - сеть «сильный»; за игрока -
тоже сеть «средний» (чтобы кадр был из живой партии, а не расставлен руками).
"""
import argparse
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# offscreen сам не видит системные шрифты - без этого вместо букв квадраты
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from game.app import MainWindow  # noqa: E402
from game.models import Models  # noqa: E402
from game.store import Store  # noqa: E402


class Silent:
    volume = 0

    def __getattr__(self, name):
        return lambda *a, **k: None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.path.join(ROOT, "models"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--steps", type=int, default=90)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    app = QApplication.instance() or QApplication([])  # noqa: F841
    store = Store(tempfile.mkdtemp())
    store.stats.update({"matches": 7, "rounds": 19, "food": 143, "longest": 38})
    models = Models(args.models)
    win = MainWindow(store, models, sounds=Silent())
    win.resize(1040, 720)
    win.show()

    def shot(name):
        app.processEvents()
        path = os.path.join(args.out, f"preview_{name}.png")
        win.grab().save(path)
        print(path)

    shot("menu")
    win.play()
    screen = win.match_screen
    player = models.load_opponent("medium")
    screen.advance(3000)                       # отсчёт
    for _ in range(args.steps):
        m = screen.match
        if m.phase != "playing":
            break
        m.press(player.act(m.field, 0))
        screen.advance(m.speed_ms)
    shot("match")
    screen.stop()
    win.show_stats()
    shot("stats")
    win.show_settings()
    shot("settings")
    win.close()


if __name__ == "__main__":
    main()
