"""Картинки для README: экраны окна без показа на экране (Qt offscreen).

    python tools/make_previews.py [--models game/models] [--out docs]

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

from game.ai.models import Models  # noqa: E402
from main import open_window  # noqa: E402


class Silent:
    volume = 0

    def __getattr__(self, name):
        return lambda *a, **k: None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.path.join(ROOT, "game", "models"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--steps", type=int, default=90)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    os.environ["SNAKEAIGAME_HOME"] = tempfile.mkdtemp(prefix="snakeai-previews-")

    app = QApplication.instance() or QApplication([])  # noqa: F841
    win, ctx = open_window(migrate_old=False)
    gw = win.game
    gw.sounds = gw.match_screen.sounds = Silent()
    gw.models = gw.stats_screen.models = models = Models(args.models)
    gw.store.stats.update({"matches": 7, "rounds": 19, "food": 143, "longest": 38})
    win.resize(1040, 720)
    win.show()

    def shot(name):
        app.processEvents()
        path = os.path.join(args.out, f"preview_{name}.png")
        win.grab().save(path)
        print(path)

    player = models.load_opponent("medium")
    for theme_name, lang in (("dark", "ru"), ("light", "ru"), ("dark", "en")):
        ctx.set_theme(theme_name)
        ctx.set_lang(lang)
        suffix = ("" if theme_name == "dark" else "_light") + ("" if lang == "ru" else "_en")
        gw.show_menu()
        shot("menu" + suffix)
        gw.play()
        screen = gw.match_screen
        screen.advance(3000)                       # отсчёт
        for _ in range(args.steps):
            m = screen.match
            if m.phase != "playing":
                break
            m.press(player.act(m.field, 0))
            screen.advance(m.speed_ms)
        shot("match" + suffix)
        screen.stop()
        gw.show_stats()
        shot("stats" + suffix)
        gw.show_settings()
        shot("settings" + suffix)
    win.close()


if __name__ == "__main__":
    main()
