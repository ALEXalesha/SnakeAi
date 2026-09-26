"""Экраны окна: меню, матч, статистика, настройки."""
import numpy as np
from PySide6.QtCore import QElapsedTimer, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QProgressBar, QPushButton, QScrollArea, QSlider,
                               QVBoxLayout, QWidget)

from game import match as M
from game import store as st
from game.board import PALETTES, Board
from game.chart import Chart, points_from
from world.cells import DOWN, LEFT, RIGHT, UP, build

# Клавиши -> направление. Кириллица - это W A S D на русской раскладке (Ц Ф Ы В).
KEY_DIRS = {
    int(Qt.Key.Key_Up): UP, int(Qt.Key.Key_W): UP, 0x0426: UP,
    int(Qt.Key.Key_Down): DOWN, int(Qt.Key.Key_S): DOWN, 0x042B: DOWN,
    int(Qt.Key.Key_Left): LEFT, int(Qt.Key.Key_A): LEFT, 0x0424: LEFT,
    int(Qt.Key.Key_Right): RIGHT, int(Qt.Key.Key_D): RIGHT, 0x0412: RIGHT,
}
# Коды клавиш Windows - не зависят от раскладки (на всякий случай для других раскладок).
VK_DIRS = {0x57: UP, 0x53: DOWN, 0x41: LEFT, 0x44: RIGHT}

TARGET = 3


def label(text="", name=None, wrap=False):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def section(text):
    return label(text.upper(), "section")


def separator():
    line = QFrame()
    line.setObjectName("separator")
    return line


def button(text, primary=False, focus=True):
    b = QPushButton(text)
    if primary:
        b.setObjectName("primary")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if not focus:
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return b


def card():
    f = QFrame()
    f.setObjectName("card")
    return f


def header(title, back):
    """Заголовок экрана с кнопкой «В меню» справа."""
    row = QHBoxLayout()
    row.addWidget(label(title, "screenTitle"))
    row.addStretch(1)
    b = button("В меню")
    b.clicked.connect(back)
    row.addWidget(b)
    return row


def mini_board():
    """Маленькое поле-картинка: две змейки тянутся к еде (для меню и настроек)."""
    field = build(4, 14, [[(3, 1), (3, 2), (3, 3), (2, 3), (2, 4), (2, 5)],
                          [(0, 12), (1, 12), (2, 12), (2, 11), (2, 10), (2, 9)]], food=[(2, 7)])
    b = Board(framed=False)
    b.setMinimumSize(0, 0)
    b.setFixedSize(14 * 20, 4 * 20)
    b.set_state(field)
    return b


def pct(v, digits=1):
    return f"{v * 100:.{digits}f}%"


# --- меню -----------------------------------------------------------------------------


class MenuScreen(QWidget):
    play = Signal()
    stats = Signal()
    settings = Signal()
    quit = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 24)
        outer.addStretch(3)

        self.logo = mini_board()
        outer.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(12)
        title = label("Нейро-змейка", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(title)
        sub = label("Вы против нейросети.\nПоле двигает сеть-мир: в игре нет ни строчки "
                    "правил змейки.", "subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(sub)
        outer.addSpacing(26)

        column = QVBoxLayout()
        column.setSpacing(10)
        self.play_button = button("Играть", primary=True)
        self.stats_button = button("Статистика")
        self.settings_button = button("Настройки")
        self.quit_button = button("Выход")
        for b, sig in ((self.play_button, self.play), (self.stats_button, self.stats),
                       (self.settings_button, self.settings), (self.quit_button, self.quit)):
            b.setFixedWidth(300)
            b.clicked.connect(sig)
            column.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addLayout(column)
        outer.addSpacing(16)

        self.message = label("", "warning", wrap=True)
        self.message.setFixedWidth(560)      # с переносом строк и выравниванием по центру
                                             # иначе Qt считает высоту на одну строку
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.message.hide()
        outer.addWidget(self.message, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(4)

        self.info = label("", "muted")
        self.info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(self.info)

    def show_message(self, text):
        self.message.setText(text)
        self.message.setVisible(bool(text))

    def set_info(self, settings):
        self.info.setText(f"Соперник: {st.LEVEL_NAMES[settings['opponent']]}   ·   "
                          f"ход {settings['speed_ms']} мс   ·   матч до {TARGET} побед")
        self.logo.set_palette(settings["palette"])


# --- матч -----------------------------------------------------------------------------


class Overlay(QWidget):
    """Затемнение поверх поля с карточкой: пауза, конец матча или сбой сети."""

    def __init__(self, parent):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        self.card = QFrame()
        self.card.setObjectName("overlayCard")
        self.card.setFixedWidth(340)
        box = QVBoxLayout(self.card)
        box.setContentsMargins(26, 22, 26, 22)
        box.setSpacing(10)
        self.title = label("", "overlayTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.text = label("", "muted", wrap=True)
        self.text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(self.title)
        box.addWidget(self.text)
        box.addSpacing(8)
        self.buttons = box
        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(6, 8, 12, 165))
        p.end()


class MatchScreen(QWidget):
    to_menu = Signal()
    again = Signal()

    def __init__(self, store, sounds, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.store = store
        self.sounds = sounds
        self.match = None
        self.level = "medium"
        self._shown = -1
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 14, 14, 14)
        row.setSpacing(14)
        self.board = Board()
        self.board.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row.addWidget(self.board, 1)
        row.addWidget(self._build_panel())

        self.overlay = Overlay(self.board)
        self.board.overlay = self.overlay
        self.resume_button = button("Продолжить", primary=True)
        self.again_button = button("Ещё матч", primary=True)
        self.menu_button = button("В меню")
        for b in (self.resume_button, self.again_button, self.menu_button):
            self.overlay.buttons.addWidget(b)
        self.resume_button.clicked.connect(self.resume)
        self.again_button.clicked.connect(self.again)
        self.menu_button.clicked.connect(self.leave)
        self.overlay.hide()

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self._tick)
        self.clock = QElapsedTimer()

    def _build_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(272)
        box = QVBoxLayout(panel)
        box.setContentsMargins(20, 18, 20, 18)
        box.setSpacing(8)

        box.addWidget(section("Счёт"))
        self.score = label("", "big")
        self.score.setTextFormat(Qt.TextFormat.RichText)
        self.score.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(self.score)
        names = QHBoxLayout()
        self.name0 = label("Вы", "value")
        self.name1 = label("Сеть", "value")
        names.addWidget(self.name0)
        names.addStretch(1)
        names.addWidget(self.name1)
        box.addLayout(names)
        self.round_info = label("", "muted")
        box.addWidget(self.round_info)
        box.addSpacing(6)
        box.addWidget(separator())

        box.addWidget(section("Длина змеек"))
        grid = QGridLayout()
        self.len0 = label("3", "value")
        self.len1 = label("3", "value")
        grid.addWidget(label("Вы"), 0, 0)
        grid.addWidget(self.len0, 0, 1, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(label("Сеть"), 1, 0)
        grid.addWidget(self.len1, 1, 1, Qt.AlignmentFlag.AlignRight)
        box.addLayout(grid)
        box.addSpacing(6)
        box.addWidget(separator())

        box.addWidget(section("Уверенность сети-мира"))
        conf_row = QHBoxLayout()
        self.conf_bar = QProgressBar()
        self.conf_bar.setRange(0, 1000)
        self.conf_bar.setTextVisible(False)
        self.conf_value = label("-", "value")
        self.conf_value.setMinimumWidth(56)
        self.conf_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        conf_row.addWidget(self.conf_bar, 1)
        conf_row.addWidget(self.conf_value)
        box.addLayout(conf_row)
        hint = label("вероятность ответа в самой неуверенной клетке поля", "muted", wrap=True)
        box.addWidget(hint)
        box.addSpacing(6)
        box.addWidget(separator())

        box.addWidget(section("Соперник"))
        self.opponent_info = label("", "value")
        box.addWidget(self.opponent_info)
        box.addStretch(1)

        keys = label("Стрелки или WASD - поворот\nEsc - пауза", "muted")
        box.addWidget(keys)
        self.pause_button = button("Пауза", focus=False)
        self.pause_button.clicked.connect(self.pause)
        box.addWidget(self.pause_button)
        return panel

    # --- управление ------------------------------------------------------------------

    def start(self, world, opponent, level):
        s = self.store.settings
        self.level = level
        self.match = M.Match(world, opponent, np.random.default_rng(), target=TARGET,
                             speed_ms=s["speed_ms"])
        self.board.set_palette(s["palette"])
        self.overlay.hide()
        self._shown = -1
        self._process()
        self._refresh()
        self.clock.start()
        self.timer.start()
        self.setFocus()

    def stop(self):
        self.timer.stop()

    def leave(self):
        self.stop()
        self.match = None
        self.overlay.hide()
        self.to_menu.emit()

    def pause(self):
        m = self.match
        if m is None or m.paused or m.phase == M.MATCH_OVER:
            return
        m.paused = True
        self._show_overlay("Пауза", "Esc - продолжить", (self.resume_button, self.menu_button))

    def resume(self):
        if self.match is None:
            return
        self.match.paused = False
        self.overlay.hide()
        self.clock.restart()
        self.setFocus()

    def auto_pause(self):
        """Окно ушло в фон - змейка не должна разбиться сама."""
        if self.match is not None and self.match.phase in (M.COUNTDOWN, M.PLAYING):
            self.pause()

    def _show_overlay(self, title, text, buttons):
        self.overlay.title.setText(title)
        self.overlay.text.setText(text)
        for b in (self.resume_button, self.again_button, self.menu_button):
            b.setVisible(b in buttons)
        self.overlay.setGeometry(self.board.rect())
        self.overlay.show()
        self.overlay.raise_()
        buttons[0].setFocus()

    # --- время -----------------------------------------------------------------------

    def _tick(self):
        dt = self.clock.restart()
        self.advance(min(dt, 250))

    def advance(self, dt_ms):
        """Шаг времени: из таймера или из тестов."""
        if self.match is None:
            return
        try:
            self.match.update(dt_ms)
        except Exception as err:  # noqa: BLE001 - сбой сети не роняет окно
            self.stop()
            self._show_overlay("Сбой сети", str(err) or type(err).__name__, (self.menu_button,))
            return
        self._process()
        if self.match.version != self._shown:
            self._refresh()

    def _process(self):
        m = self.match
        stats = self.store.stats
        for ev in m.take_events():
            self.sounds.on_event(ev)
            if ev.startswith("round_"):
                st.record_round(stats, self.level, m.round_result, m.longest[0], m.round_eaten[0])
                self.store.save_stats()
            elif ev in ("win", "lose"):
                st.record_match(stats, self.level, ev == "win")
                self.store.save_stats()
                a, b = m.score
                self._show_overlay("Победа!" if ev == "win" else "Поражение",
                                   f"Счёт {a} : {b}   ·   соперник "
                                   f"{st.LEVEL_NAMES[self.level].lower()}",
                                   (self.again_button, self.menu_button))

    # --- вид ---------------------------------------------------------------------------

    def _refresh(self):
        m = self.match
        s = self.store.settings
        self._shown = m.version
        text = sub = ""
        if m.phase == M.COUNTDOWN:
            text, sub = str(m.count), f"Раунд {m.round}"
        elif m.phase == M.ROUND_OVER:
            text = {"win": "Раунд ваш!", "lose": "Раунд за сетью", "draw": "Ничья"}[m.round_result]
            sub = "обе змейки врезались - очко никому" if m.round_result == "draw" else \
                f"счёт {m.score[0]} : {m.score[1]}"
        self.board.set_state(m.field, m.food_probs, s["show_food_map"], m.crashed, text, sub)

        pal = PALETTES[self.board.palette_index]
        c0, c1 = pal["label"]
        self.score.setText(f"<span style='color:{c0}'>{m.score[0]}</span>"
                           f"<span style='color:#5b6577'> : </span>"
                           f"<span style='color:{c1}'>{m.score[1]}</span>")
        self.name0.setStyleSheet(f"color: {c0};")
        self.name1.setStyleSheet(f"color: {c1};")
        self.round_info.setText(f"Раунд {m.round}   ·   до {m.target} побед")
        l0, l1 = m.lengths()
        self.len0.setText(str(l0))
        self.len1.setText(str(l1))
        conf = m.confidence
        if conf is None:
            self.conf_bar.setValue(0)
            self.conf_value.setText("-")
            level = "good"
        else:
            self.conf_bar.setValue(int(round(conf * 1000)))
            self.conf_value.setText(pct(conf))
            level = "good" if conf >= 0.9 else "mid" if conf >= 0.6 else "bad"
        if self.conf_bar.property("level") != level:
            self.conf_bar.setProperty("level", level)
            self.conf_bar.style().unpolish(self.conf_bar)
            self.conf_bar.style().polish(self.conf_bar)
        self.opponent_info.setText(f"{st.LEVEL_NAMES[self.level]}   ·   ход {m.speed_ms} мс")

    def apply_settings(self):
        self.board.set_palette(self.store.settings["palette"])
        if self.match is not None:
            self._refresh()

    def keyPressEvent(self, event):
        key = int(event.key())
        if key == int(Qt.Key.Key_Escape):
            if self.match is None:
                return
            if self.match.phase == M.MATCH_OVER or self.overlay.isVisible() and \
                    not self.match.paused:
                self.leave()
            elif self.match.paused:
                self.resume()
            else:
                self.pause()
            return
        d = KEY_DIRS.get(key)
        if d is None:
            d = VK_DIRS.get(int(event.nativeVirtualKey()))
        if d is not None and self.match is not None:
            self.match.press(d)
            event.accept()
            return
        super().keyPressEvent(event)


# --- статистика -----------------------------------------------------------------------


class StatsScreen(QWidget):
    back = Signal()

    def __init__(self, store, models, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.store = store
        self.models = models
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 16)
        outer.addLayout(header("Статистика", self.back.emit))
        outer.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("scrollBody")
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        box = QVBoxLayout(body)
        box.setContentsMargins(0, 0, 8, 8)
        box.setSpacing(14)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.values = {}
        for key, caption in (("matches", "матчей сыграно"), ("rounds", "раундов"),
                             ("longest", "самая длинная змейка"), ("food", "съедено еды")):
            c = card()
            v = QVBoxLayout(c)
            v.setContentsMargins(16, 12, 16, 12)
            self.values[key] = label("0", "cardValue")
            v.addWidget(self.values[key])
            v.addWidget(label(caption, "muted"))
            cards.addWidget(c, 1)
        box.addLayout(cards)

        levels = card()
        grid = QGridLayout(levels)
        grid.setContentsMargins(18, 14, 18, 14)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        heads = ("Соперник", "Матчи\nпобеды / поражения", "Раунды\nпобеды / поражения / ничьи",
                 "Выигрыш\nу бота")
        for col, text in enumerate(heads):
            grid.addWidget(section(text), 0, col, Qt.AlignmentFlag.AlignBottom)
        grid.setColumnStretch(3, 1)
        self.level_cells = {}
        for row, lv in enumerate(st.LEVELS, start=1):
            grid.addWidget(label(st.LEVEL_NAMES[lv], "value"), row, 0)
            for col, key in enumerate(("matches", "rounds", "win_vs_bot"), start=1):
                cell = label("0")
                self.level_cells[lv, key] = cell
                grid.addWidget(cell, row, col)
        box.addWidget(levels)

        world = card()
        wv = QVBoxLayout(world)
        wv.setContentsMargins(18, 14, 18, 14)
        wv.addWidget(section("Точность сети-мира на отложенных партиях 32x32"))
        self.world_label = label("", wrap=True)
        self.world_label.setTextFormat(Qt.TextFormat.RichText)
        wv.addWidget(self.world_label)
        box.addWidget(world)

        charts = QGridLayout()
        charts.setSpacing(12)
        self.chart_world_loss = Chart("Сеть-мир: ошибка обучения", "#ff8a3d", "шаг", log_y=True)
        self.chart_world_field = Chart("Сеть-мир: поле совпало целиком", "#34d17c", "шаг",
                                       percent=True)
        self.chart_imitation = Chart("Соперник: подражание боту, точность", "#4fc3f7", "шаг",
                                     percent=True)
        self.chart_rl = Chart("Соперник: пробы и ошибки, награда", "#c792ea", "партия")
        self.charts = [self.chart_world_loss, self.chart_world_field, self.chart_imitation,
                       self.chart_rl]
        for i, c in enumerate(self.charts):
            charts.addWidget(c, i // 2, i % 2)
        box.addLayout(charts)
        self.no_charts = label("Графиков обучения пока нет: паспорта моделей появятся в папке "
                               "models после обучения.", "muted", wrap=True)
        box.addWidget(self.no_charts)
        box.addStretch(1)

    def refresh(self):
        s = self.store.stats
        for key, v in self.values.items():
            v.setText(str(s[key]))
        player = self.models.load_passport("player") or {}
        levels = player.get("levels") if isinstance(player.get("levels"), dict) else {}
        for lv in st.LEVELS:
            n = s["levels"][lv]
            self.level_cells[lv, "matches"].setText(f"{n['match_wins']} / {n['match_losses']}")
            self.level_cells[lv, "rounds"].setText(f"{n['wins']} / {n['losses']} / {n['draws']}")
            info = levels.get(lv) if isinstance(levels.get(lv), dict) else {}
            win = info.get("win_vs_bot")
            ok = isinstance(win, (int, float)) and not isinstance(win, bool)
            self.level_cells[lv, "win_vs_bot"].setText(pct(win, 0) if ok else "-")

        world = self.models.load_passport("world") or {}
        final = world.get("final") if isinstance(world.get("final"), dict) else {}
        self.world_label.setText(self._accuracy(final))
        self.chart_world_loss.set_points(points_from(world.get("curve"), "step", "loss"))
        self.chart_world_field.set_points(points_from(world.get("curve"), "step", "field"))
        self.chart_imitation.set_points(points_from(player.get("imitation_curve"), "step",
                                                    "accuracy"))
        self.chart_rl.set_points(points_from(player.get("rl_curve"), "episode", "reward"))
        self.no_charts.setVisible(self.visible_charts() == 0)

    @staticmethod
    def _accuracy(final):
        rows = (("field_symmetric", "поле совпало целиком, в игре (8 видов поля)", 0.995, True),
                ("field", "поле совпало целиком, один проход", 0.995, True),
                ("events", "события (съел, врезался)", 0.999, True),
                ("food_on_occupied", "вероятность еды на занятых клетках", 0.01, False))
        parts = []
        for key, name, goal, above in rows:
            v = final.get(key)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            ok = v >= goal if above else v < goal
            color = "#5fd08f" if ok else "#e2b340"
            sign = "≥" if above else "&lt;"            # это RichText: «<» открыл бы тег
            parts.append(f"{name}: <b style='color:{color}'>{v * 100:.2f}%</b> "
                         f"<span style='color:#8b96a8'>(цель {sign} {goal * 100:g}%)</span>")
        if not parts:
            return "<span style='color:#8b96a8'>Паспорта сети-мира пока нет: модель ещё не " \
                   "обучена.</span>"
        return "<br>".join(parts)

    def accuracy_text(self):
        return self.world_label.text()

    def visible_charts(self):
        return sum(not c.isHidden() for c in self.charts)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.back.emit()
            return
        super().keyPressEvent(event)


# --- настройки ------------------------------------------------------------------------


class SettingsScreen(QWidget):
    back = Signal()
    changed = Signal(str)

    def __init__(self, store, sounds, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.store = store
        self.sounds = sounds
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.addLayout(header("Настройки", self.back.emit))
        outer.addSpacing(10)

        form = card()
        form.setMaximumWidth(720)
        grid = QGridLayout(form)
        grid.setContentsMargins(24, 20, 24, 20)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(18)
        grid.setColumnStretch(1, 1)

        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(*st.SPEED_RANGE)
        self.speed.setSingleStep(5)
        self.speed.setPageStep(10)
        self.speed_value = label("", "value")
        self._row(grid, 0, "Скорость", self.speed, self.speed_value,
                  "миллисекунд на ход: меньше - быстрее")

        self.opponent = QComboBox()
        for lv in st.LEVELS:
            self.opponent.addItem(st.LEVEL_NAMES[lv], lv)
        self._row(grid, 1, "Соперник", self.opponent, None,
                  "новичок - ранний снимок подражания, сильный - после проб и ошибок")

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(*st.VOLUME_RANGE)
        self.volume_value = label("", "value")
        self._row(grid, 2, "Громкость", self.volume, self.volume_value, None)

        self.palette = QComboBox()
        for pal in PALETTES:
            self.palette.addItem(pal["name"])
        self.preview = mini_board()
        self._row(grid, 3, "Цвета поля", self.palette, None, None)
        grid.addWidget(self.preview, 4, 1, Qt.AlignmentFlag.AlignLeft)

        self.food_map = QCheckBox("Показывать, где сеть-мир родит еду")
        self._row(grid, 5, "Карта еды", self.food_map, None,
                  "полупрозрачная подсветка поверх поля: чем ярче, тем вероятнее")
        outer.addWidget(form)
        outer.addStretch(1)

        self.speed.valueChanged.connect(lambda v: self._set("speed_ms", v))
        self.opponent.currentIndexChanged.connect(
            lambda i: self._set("opponent", self.opponent.itemData(i)))
        self.volume.valueChanged.connect(lambda v: self._set("volume", v))
        self.volume.sliderReleased.connect(lambda: self.sounds.play("eat"))
        self.palette.currentIndexChanged.connect(lambda i: self._set("palette", i))
        self.food_map.toggled.connect(lambda on: self._set("show_food_map", bool(on)))

    @staticmethod
    def _row(grid, row, name, widget, value, hint):
        grid.addWidget(label(name, "value"), row, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        line = QHBoxLayout()
        line.addWidget(widget, 1 if isinstance(widget, QSlider) else 0)
        if value is not None:
            value.setMinimumWidth(110)
            line.addWidget(value)
        if not isinstance(widget, QSlider):
            line.addStretch(1)
        col.addLayout(line)
        if hint:
            col.addWidget(label(hint, "muted", wrap=True))
        grid.addLayout(col, row, 1)

    def load(self):
        """Показать сохранённые значения, ничего не записывая."""
        s = self.store.settings
        widgets = (self.speed, self.opponent, self.volume, self.palette, self.food_map)
        for w in widgets:
            w.blockSignals(True)
        self.speed.setValue(s["speed_ms"])
        self.opponent.setCurrentIndex(st.LEVELS.index(s["opponent"]))
        self.volume.setValue(s["volume"])
        self.palette.setCurrentIndex(s["palette"])
        self.food_map.setChecked(s["show_food_map"])
        for w in widgets:
            w.blockSignals(False)
        self._labels()

    def _labels(self):
        s = self.store.settings
        self.speed_value.setText(f"{s['speed_ms']} мс")
        self.volume_value.setText(f"{s['volume']}%")
        self.preview.set_palette(s["palette"])

    def _set(self, key, value):
        self.store.set(key, value)
        if key == "volume":
            self.sounds.set_volume(self.store.settings["volume"])
        self._labels()
        self.changed.emit(key)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.back.emit()
            return
        super().keyPressEvent(event)
