"""Нейро-змейка: запуск окна. Поле двигает сеть-мир, кода правил в игре нет."""
import os
import sys


def main():
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
