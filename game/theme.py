"""Тёмная тема окна (QSS) и палитра Qt для стиля Fusion."""
from PySide6.QtGui import QColor, QPalette

BG = "#0f1319"
CARD = "#161b23"
LINE = "#252d3a"
TEXT = "#e6ebf2"
MUTED = "#8b96a8"
ACCENT = "#2fbf71"

QSS = f"""
QMainWindow, QWidget#screen, QWidget#scrollBody {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10.5pt; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {LINE}; padding: 4px 6px; }}

QLabel#title {{ font-size: 36pt; font-weight: 700; color: #7ee2a8; }}
QLabel#screenTitle {{ font-size: 20pt; font-weight: 600; }}
QLabel#subtitle, QLabel#muted {{ color: {MUTED}; }}
QLabel#section {{ color: {MUTED}; font-size: 9pt; font-weight: 600; letter-spacing: 1px; }}
QLabel#big {{ font-size: 30pt; font-weight: 700; }}
QLabel#cardValue {{ font-size: 22pt; font-weight: 700; }}
QLabel#value {{ font-weight: 600; }}
QLabel#warning {{ background: #3a2417; color: #ffcf9e; border: 1px solid #6b3f22;
                 border-radius: 10px; padding: 10px 14px; }}
QLabel#overlayTitle {{ font-size: 26pt; font-weight: 700; }}

QFrame#panel, QFrame#card, QFrame#overlayCard {{ background: {CARD}; border: 1px solid {LINE};
                                               border-radius: 14px; }}
QFrame#panel QLabel, QFrame#card QLabel, QFrame#overlayCard QLabel {{ background: transparent;
                                                                    border: none; }}
QFrame#separator {{ background: {LINE}; border: none; max-height: 1px; min-height: 1px; }}

QPushButton {{ background: #1d2430; border: 1px solid #2c3544; border-radius: 10px;
              padding: 10px 18px; font-size: 11pt; }}
QPushButton:hover {{ background: #253042; border-color: #3d4a5e; }}
QPushButton:pressed {{ background: #161c26; }}
QPushButton:focus {{ border-color: #4a5a72; }}
QPushButton#primary {{ background: {ACCENT}; color: #06110a; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #3fd183; }}
QPushButton#primary:pressed {{ background: #28a862; }}
QPushButton#flat {{ background: transparent; border: none; color: {MUTED}; padding: 6px 10px; }}
QPushButton#flat:hover {{ color: {TEXT}; }}

QSlider::groove:horizontal {{ height: 6px; background: #2a3342; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 18px; height: 18px; margin: -7px 0; border-radius: 9px;
                             background: {TEXT}; }}
QSlider::handle:horizontal:hover {{ background: #ffffff; }}

QComboBox {{ background: #1d2430; border: 1px solid #2c3544; border-radius: 8px;
            padding: 6px 12px; min-width: 150px; }}
QComboBox:hover {{ border-color: #3d4a5e; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: #1d2430; border: 1px solid #2c3544;
                              selection-background-color: #2a5a3f; outline: none; }}

QCheckBox {{ spacing: 10px; }}

QProgressBar {{ background: #232b37; border: none; border-radius: 5px; max-height: 10px;
               min-height: 10px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QProgressBar[level="mid"]::chunk {{ background: #e2b340; }}
QProgressBar[level="bad"]::chunk {{ background: #e5484d; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c3544; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def palette():
    """Тёмная палитра Qt: у стиля Fusion по ней рисуется всё, что не описано в QSS."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG, QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: "#1d2430", QPalette.ColorRole.AlternateBase: CARD,
        QPalette.ColorRole.Text: TEXT, QPalette.ColorRole.Button: "#1d2430",
        QPalette.ColorRole.ButtonText: TEXT, QPalette.ColorRole.Highlight: "#2a5a3f",
        QPalette.ColorRole.HighlightedText: "#ffffff", QPalette.ColorRole.ToolTipBase: CARD,
        QPalette.ColorRole.ToolTipText: TEXT, QPalette.ColorRole.PlaceholderText: MUTED,
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    return p


def apply(app):
    """Стиль и палитра всего приложения. QSS ставит само главное окно (так и в тестах)."""
    app.setStyle("Fusion")
    app.setPalette(palette())
