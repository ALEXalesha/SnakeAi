"""Главное окно: стопка экранов, загрузка моделей, место окна между запусками."""
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from game import theme
from game.models import ModelMissing
from game.screens import MatchScreen, MenuScreen, SettingsScreen, StatsScreen
from game.sound import Sounds
from game.window_state import Remember

WIDTH, HEIGHT = 1040, 720
MIN_WIDTH, MIN_HEIGHT = 820, 600


def make_icon():
    """Значок окна рисуется кодом: голова змейки на тёмном квадрате."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = size / 32
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#10141b"))
        p.drawRoundedRect(QRectF(0, 0, size, size), 7 * s, 7 * s)
        p.setBrush(QColor("#34d17c"))
        p.drawRoundedRect(QRectF(4 * s, 13 * s, 16 * s, 8 * s), 4 * s, 4 * s)
        p.setBrush(QColor("#9af7c1"))
        p.drawEllipse(QPointF(21 * s, 17 * s), 6 * s, 6 * s)
        p.setBrush(QColor("#0b0e13"))
        p.drawEllipse(QPointF(23 * s, 15 * s), 1.4 * s, 1.4 * s)
        p.setBrush(QColor("#ff4d6d"))
        p.drawEllipse(QPointF(26 * s, 7 * s), 3 * s, 3 * s)
        p.end()
        icon.addPixmap(pix)
    return icon


class MainWindow(QMainWindow):
    def __init__(self, store, models, sounds=None, window_path=None):
        super().__init__()
        self.store = store
        self.models = models
        self.sounds = sounds if sounds is not None else Sounds(store.settings["volume"])
        self._world = None
        self._opponents = {}
        self.setWindowTitle("Нейро-змейка")
        self.setWindowIcon(make_icon())
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(WIDTH, HEIGHT)
        self.setStyleSheet(theme.QSS)

        self.stack = QStackedWidget()
        self.menu = MenuScreen()
        self.match_screen = MatchScreen(store, self.sounds)
        self.stats_screen = StatsScreen(store, models)
        self.settings_screen = SettingsScreen(store, self.sounds)
        for screen in (self.menu, self.match_screen, self.stats_screen, self.settings_screen):
            self.stack.addWidget(screen)
        self.setCentralWidget(self.stack)

        self.menu.play.connect(self.play)
        self.menu.stats.connect(self.show_stats)
        self.menu.settings.connect(self.show_settings)
        self.menu.quit.connect(self.close)
        self.match_screen.to_menu.connect(self.show_menu)
        self.match_screen.again.connect(self.play)
        self.stats_screen.back.connect(self.show_menu)
        self.settings_screen.back.connect(self.show_menu)
        self.settings_screen.changed.connect(self._setting_changed)

        self.match_screen.board.set_palette(store.settings["palette"])
        self.remember = None
        if window_path is not None:
            self.remember = Remember(self, window_path, {"width": WIDTH, "height": HEIGHT,
                                                         "minWidth": MIN_WIDTH,
                                                         "minHeight": MIN_HEIGHT})
        self.show_menu()

    # --- экраны ------------------------------------------------------------------------

    def show_window(self):
        if self.remember is not None:
            self.remember.show()
        else:
            self.show()

    def show_menu(self):
        self.match_screen.stop()
        self.menu.set_info(self.store.settings)
        self.stack.setCurrentWidget(self.menu)
        self.menu.play_button.setFocus()

    def show_stats(self):
        self.menu.show_message("")
        self.stats_screen.refresh()
        self.stack.setCurrentWidget(self.stats_screen)
        self.stats_screen.setFocus()

    def show_settings(self):
        self.menu.show_message("")
        self.settings_screen.load()
        self.stack.setCurrentWidget(self.settings_screen)
        self.settings_screen.setFocus()

    def play(self):
        level = self.store.settings["opponent"]
        try:
            if self._world is None:
                self._world = self.models.load_world()
            if level not in self._opponents:
                self._opponents[level] = self.models.load_opponent(level)
        except ModelMissing as err:
            self._fail(str(err))
            return
        except Exception as err:  # noqa: BLE001 - любая беда с моделью - текст в окне
            self._fail(f"Не удалось загрузить модель: {err}")
            return
        self.menu.show_message("")
        self.stack.setCurrentWidget(self.match_screen)
        self.match_screen.start(self._world, self._opponents[level], level)

    def _fail(self, text):
        self.show_menu()
        self.menu.show_message(text)

    def _setting_changed(self, key):
        if key == "palette":
            self.match_screen.apply_settings()
            self.menu.set_info(self.store.settings)

    # --- окно ----------------------------------------------------------------------------

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow() \
                and self.stack.currentWidget() is self.match_screen:
            self.match_screen.auto_pause()
        super().changeEvent(event)

    def moveEvent(self, event):
        if self.remember is not None:
            self.remember.track()
        super().moveEvent(event)

    def resizeEvent(self, event):
        if self.remember is not None:
            self.remember.track()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.match_screen.stop()
        if self.remember is not None:
            self.remember.save()
        super().closeEvent(event)


def run(store, models, window_path=None):
    """Показать окно и крутить цикл Qt до закрытия."""
    app = QApplication.instance()
    window = MainWindow(store, models, window_path=window_path)
    window.show_window()
    return app.exec()
