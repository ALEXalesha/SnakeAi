import os
import sys

# Без экрана: Qt рисует в память.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# offscreen сам не видит системные шрифты: без этого буквы - пустые квадраты, и тесты
# на размер надписей мерили бы квадраты, а не Segoe UI, как на экране у игрока.
_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
if os.path.isdir(_FONTS):
    os.environ.setdefault("QT_QPA_FONTDIR", _FONTS)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
