"""Где лежат данные игрока и модели.

Данные (settings.json, stats.json, window.json) - в %LOCALAPPDATA%\\SnakeAIGame. Если рядом
с exe лежит portable.txt - в папке saves рядом с exe (как в AiCar). Модели - в models рядом
с кодом, а в сборке PyInstaller - внутри распакованной сборки (sys._MEIPASS).
"""
import os
import sys

APP_NAME = "SnakeAIGame"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def frozen():
    return bool(getattr(sys, "frozen", False))


def exe_dir():
    """Папка exe в сборке, папка проекта при запуске из исходников."""
    return os.path.dirname(os.path.abspath(sys.executable)) if frozen() else ROOT


def resource_dir():
    if frozen():
        return getattr(sys, "_MEIPASS", exe_dir())
    return ROOT


def models_dir():
    return os.path.join(resource_dir(), "models")


def data_dir(exe_folder=None, environ=None):
    beside = exe_dir() if exe_folder is None else os.fspath(exe_folder)
    if os.path.exists(os.path.join(beside, "portable.txt")):
        return os.path.join(beside, "saves")
    env = os.environ if environ is None else environ
    base = env.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)
