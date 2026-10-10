"""Поле: рисует то, что выдала сеть-мир, - клетки, змеек по указателям, еду и (по желанию)
полупрозрачную карту «где родится еда». Размер поля берётся из самого поля; клетки всегда
квадратные, поле по центру виджета.
"""
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from game.core import cells

PALETTES = [
    {"name": "Ночь", "bg": "#10141b", "cell_a": "#171d27", "cell_b": "#141923",
     "border": "#2a3342", "head": ("#9af7c1", "#ffc58a"), "body": ("#34d17c", "#ff8a3d"),
     "tail": ("#1d6b45", "#8a4a22"), "label": ("#7ee2a8", "#ffab6b"),
     "food": "#ff4d6d", "food_map": "#ffd54f", "crash": "#ff3b3b", "text": "#f2f5fa",
     "eye": "#0b0e13"},
    {"name": "Океан", "bg": "#0a1a26", "cell_a": "#0f2535", "cell_b": "#0c2130",
     "border": "#1f4058", "head": ("#c7f0ff", "#ffd1e3"), "body": ("#4fc3f7", "#f06292"),
     "tail": ("#1d5a78", "#7a2d4c"), "label": ("#7fd6fb", "#f48fb1"),
     "food": "#ffee58", "food_map": "#80deea", "crash": "#ff5252", "text": "#eef8ff",
     "eye": "#06131c"},
    {"name": "Светлая", "bg": "#efe9dc", "cell_a": "#e7e0d0", "cell_b": "#e2dac8",
     "border": "#c9bfa8", "head": ("#0e5a2a", "#10357f"), "body": ("#1f8a45", "#2456c7"),
     "tail": ("#8cc49e", "#9db3e6"), "label": ("#5fd08f", "#7fa4ff"),
     "food": "#d62828", "food_map": "#ff8c1a", "crash": "#b00020", "text": "#1d1d1d",
     "eye": "#ffffff"},
]

MARGIN = 10          # отступ поля от края виджета


def _mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


class Board(QWidget):
    def __init__(self, parent=None, framed=True):
        super().__init__(parent)
        self.framed = framed
        self.field = None
        self.food_probs = None
        self.show_food_map = False
        self.crashed = (False, False)
        self.text = ""
        self.subtext = ""
        self.palette_index = 0
        self.overlay = None           # виджет паузы поверх поля (ставит экран матча)
        self._bg_cache = (None, None)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    # --- снаружи ---------------------------------------------------------------------

    def set_palette(self, index):
        self.palette_index = max(0, min(len(PALETTES) - 1, int(index)))
        self._bg_cache = (None, None)
        self.update()

    def set_state(self, field, food_probs=None, show_food_map=False, crashed=(False, False),
                  text="", subtext=""):
        self.field = field
        self.food_probs = food_probs
        self.show_food_map = show_food_map
        self.crashed = crashed
        self.text = text
        self.subtext = subtext
        self.update()

    def shape(self):
        return self.field.shape if self.field is not None else (32, 32)

    def field_rect(self):
        """Квадрат поля в координатах виджета (под размер поля, клетки квадратные)."""
        h, w = self.shape()
        m = MARGIN if self.framed else 0
        cell = max(1.0, min((self.width() - 2 * m) / w, (self.height() - 2 * m) / h))
        fw, fh = cell * w, cell * h
        return QRectF((self.width() - fw) / 2, (self.height() - fh) / 2, fw, fh)

    def resizeEvent(self, event):
        if self.overlay is not None:
            self.overlay.setGeometry(self.rect())
        self._bg_cache = (None, None)
        super().resizeEvent(event)

    # --- рисование ---------------------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = PALETTES[self.palette_index]
        rect = self.field_rect()
        h, w = self.shape()
        cell = rect.width() / w
        p.drawPixmap(0, 0, self._background(rect, pal, h, w))
        if self.field is not None:
            clip = QPainterPath()
            clip.addRoundedRect(rect, cell * 0.6, cell * 0.6)
            p.setClipPath(clip)
            if self.show_food_map and self.food_probs is not None:
                self._draw_food_map(p, rect, cell, pal)
            self._draw_food(p, rect, cell, pal)
            for s in (0, 1):
                self._draw_snake(p, rect, cell, pal, s)
            p.setClipping(False)
        if self.text:
            self._draw_text(p, rect, pal)
        p.end()

    def _background(self, rect, pal, h, w):
        key = (self.width(), self.height(), self.palette_index, h, w, self.framed,
               self.devicePixelRatioF())
        if self._bg_cache[0] == key:
            return self._bg_cache[1]
        ratio = self.devicePixelRatioF()
        pix = QPixmap(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)))
        pix.setDevicePixelRatio(ratio)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cell = rect.width() / w
        radius = cell * 0.6
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(pal["bg"]))
        p.drawRoundedRect(rect, radius, radius)
        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        p.setClipPath(clip)
        a, b = QColor(pal["cell_a"]), QColor(pal["cell_b"])
        for r in range(h):
            for c in range(w):
                p.fillRect(QRectF(rect.x() + c * cell, rect.y() + r * cell, cell + 0.5, cell + 0.5),
                           a if (r + c) % 2 == 0 else b)
        p.setClipping(False)
        if self.framed:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(pal["border"]), 2))
            p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), radius + 1, radius + 1)
        p.end()
        self._bg_cache = (key, pix)
        return pix

    @staticmethod
    def _center(rect, cell, rc):
        return QPointF(rect.x() + (rc[1] + 0.5) * cell, rect.y() + (rc[0] + 0.5) * cell)

    def _draw_food_map(self, p, rect, cell, pal):
        probs = np.asarray(self.food_probs, dtype=np.float64)
        if probs.shape != self.field.shape or not np.all(np.isfinite(probs)):
            return
        # Яркость - во сколько раз вероятность выше равномерной: у обученной сети еда
        # «равномерно по пустым клеткам», и тогда поле ровно подсвечено везде, кроме змеек.
        ratio = probs * probs.size
        level = np.clip(ratio / 4.0, 0.0, 1.0)
        base = QColor(pal["food_map"])
        for r, c in np.argwhere(ratio > 0.05):
            color = QColor(base)
            color.setAlpha(int(12 + 170 * level[r, c]))
            p.fillRect(QRectF(rect.x() + c * cell, rect.y() + r * cell, cell, cell), color)

    def _draw_food(self, p, rect, cell, pal):
        base = QColor(pal["food"])
        for r, c in np.argwhere(self.field == cells.FOOD):
            center = self._center(rect, cell, (r, c))
            glow = QColor(base)
            glow.setAlpha(55)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(center, cell * 0.55, cell * 0.55)
            grad = QRadialGradient(center - QPointF(cell * 0.1, cell * 0.1), cell * 0.4)
            grad.setColorAt(0, base.lighter(150))
            grad.setColorAt(1, base)
            p.setBrush(grad)
            p.drawEllipse(center, cell * 0.33, cell * 0.33)
            p.setBrush(QColor(255, 255, 255, 150))
            p.drawEllipse(center - QPointF(cell * 0.11, cell * 0.12), cell * 0.08, cell * 0.08)

    def _draw_snake(self, p, rect, cell, pal, s):
        field = self.field
        head = cells.head(field, s)
        body_color, tail_color = QColor(pal["body"][s]), QColor(pal["tail"][s])
        links = cells.chain(field, s)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if links is not None and len(links) > 1:
            n = len(links) - 1
            for i, (a, b) in enumerate(zip(links, links[1:])):
                t = (i + 1) / n
                pen = QPen(_mix(tail_color, body_color, t ** 0.7), cell * (0.52 + 0.24 * t))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(self._center(rect, cell, a), self._center(rect, cell, b))
        else:
            # Змейка разорвана (сбой сети): рисуем каждую клетку тела к её указателю.
            pen = QPen(body_color, cell * 0.66)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            h, w = field.shape
            for rc in cells.body_cells(field, s):
                t = cells.pointer_target(field, rc, s)
                a = self._center(rect, cell, rc)
                if 0 <= t[0] < h and 0 <= t[1] < w:
                    p.drawLine(a, self._center(rect, cell, t))
                else:
                    p.drawPoint(a)
        if head is not None:
            self._draw_head(p, rect, cell, pal, s, head)

    def _draw_head(self, p, rect, cell, pal, s, head):
        center = self._center(rect, cell, head)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(pal["head"][s]))
        p.drawEllipse(center, cell * 0.47, cell * 0.47)
        d = cells.heading(self.field, s)
        dy, dx = cells.DELTA[d] if d is not None else (0, 1 if s == 0 else -1)
        fwd = QPointF(dx, dy) * (cell * 0.16)
        side = QPointF(-dy, dx) * (cell * 0.2)
        for sign in (-1, 1):
            eye = center + fwd + side * sign
            p.setBrush(QColor(pal["eye"]))
            p.drawEllipse(eye, cell * 0.1, cell * 0.1)
        if self.crashed[s]:
            pen = QPen(QColor(pal["crash"]), max(2.0, cell * 0.14))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(center, cell * 0.72, cell * 0.72)
            k = cell * 0.28
            p.drawLine(center + QPointF(-k, -k), center + QPointF(k, k))
            p.drawLine(center + QPointF(-k, k), center + QPointF(k, -k))

    def caption_layout(self, rect):
        """Шрифты и места крупной надписи поверх поля (отсчёт, итог раунда): крупный шрифт,
        мелкий, полоса-подложка, место главной строки и место подписи."""
        big = QFont(self.font())
        big.setPixelSize(max(18, int(rect.height() * 0.093)))
        big.setBold(True)
        small = QFont(self.font())
        small.setPixelSize(max(12, int(rect.height() * 0.045)))
        band_h = rect.height() * (0.2 if self.subtext else 0.15)
        band = QRectF(rect.x(), rect.center().y() - band_h / 2, rect.width(), band_h)
        main = QRectF(band.x(), band.y(), band.width(), band.height() * (0.68 if self.subtext else 1))
        sub = QRectF(band.x(), main.bottom() - band.height() * 0.08, band.width(), band.height() * 0.4)
        return big, small, band, main, sub

    def _draw_text(self, p, rect, pal):
        big, small, band, main, sub = self.caption_layout(rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRect(band)
        p.setFont(big)
        p.setPen(QColor(0, 0, 0, 160))
        p.drawText(main.translated(2, 3), Qt.AlignmentFlag.AlignCenter, self.text)
        p.setPen(QColor("#ffffff"))
        p.drawText(main, Qt.AlignmentFlag.AlignCenter, self.text)
        if self.subtext:
            p.setFont(small)
            p.setPen(QColor(255, 255, 255, 210))
            p.drawText(sub, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.subtext)
