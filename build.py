"""Сборка: иконка, PyInstaller, portable-архив и установщик NSIS.

    python build.py
    python build.py --skip-installer

Номер версии один - в installer.nsi; по нему названы и установщик, и архив.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

APP = "SnakeAIGame"
BUILD = "build"
DIST = "dist"
ICON = os.path.join(BUILD, f"{APP}.ico")
NSIS_SCRIPT = "installer.nsi"
NSIS_PATHS = (r"C:\Program Files (x86)\NSIS\makensis.exe", r"C:\Program Files\NSIS\makensis.exe")

# Учитель и обучение в игру не входят: в игре нет кода правил (см. спек, п. 1).
EXCLUDE = ("teacher", "train", "pytest", "PIL", "tkinter", "pygame",
           "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
           "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf", "PySide6.QtCharts",
           "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtNetwork",
           "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner")


def version():
    with open(NSIS_SCRIPT, encoding="utf-8-sig") as f:
        for line in f:
            if line.startswith("!define VERSION"):
                return line.split('"')[1]
    raise SystemExit("в installer.nsi нет !define VERSION")


def make_icon(path=ICON, size=256):
    """Иконка рисуется кодом: зелёная змейка кольцом вокруг красной еды на тёмном."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(22, 26, 34))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.18, size * 0.18)
    body = QPainterPath(QPointF(size * 0.22, size * 0.78))
    body.lineTo(size * 0.22, size * 0.24)
    body.lineTo(size * 0.78, size * 0.24)
    body.lineTo(size * 0.78, size * 0.62)
    body.lineTo(size * 0.44, size * 0.62)
    pen = QPen(QColor(86, 214, 140), size * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(body)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(236, 240, 245))
    p.drawEllipse(QPointF(size * 0.44, size * 0.62), size * 0.085, size * 0.085)
    p.setBrush(QColor(240, 84, 84))
    p.drawEllipse(QPointF(size * 0.5, size * 0.44), size * 0.07, size * 0.07)
    p.end()

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    png = path + ".png"
    img.save(png)
    Image.open(png).save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return path


def run_pyinstaller(console=False):
    root = os.path.abspath(os.path.dirname(__file__))
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--name", APP, "--icon", os.path.join(root, ICON),
            "--add-data", f"{os.path.join(root, 'game', 'models')}{os.pathsep}game/models",
            "--add-data", f"{os.path.join(root, 'aikit', 'VERSION')}{os.pathsep}aikit",
            "--paths", root,
            "--distpath", os.path.join(root, DIST),
            "--workpath", os.path.join(root, BUILD, "work"),
            "--specpath", os.path.join(root, BUILD)]
    args += ["--console"] if console else ["--windowed"]
    for module in EXCLUDE:
        args += ["--exclude-module", module]
    args.append(os.path.join(root, "main.py"))
    subprocess.run(args, check=True)


def make_portable(folder=None):
    folder = folder or os.path.join(DIST, APP)
    with open(os.path.join(folder, "portable.txt"), "w", encoding="utf-8") as f:
        f.write("Пока этот файл лежит рядом с SnakeAIGame.exe, настройки и статистика пишутся в\n"
                "папку saves рядом, а не в профиль пользователя. Удалите его, чтобы вернуть\n"
                "обычное поведение.\n")
    for doc in ("README.md", "README.ru.md"):
        shutil.copy(doc, os.path.join(folder, doc))
    archive = os.path.join(DIST, f"{APP}-{version()}-portable.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.join(APP, os.path.relpath(full, folder)))
    return archive


def find_nsis():
    return shutil.which("makensis") or next((p for p in NSIS_PATHS if os.path.exists(p)), None)


def make_installer():
    nsis = find_nsis()
    if nsis is None:
        print("NSIS не найден, установщик пропущен")
        return None
    subprocess.run([nsis, NSIS_SCRIPT], check=True)
    return os.path.join(DIST, f"{APP}-{version()}-setup.exe")


def size_of(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, files in os.walk(path) for f in files)


def main():
    ap = argparse.ArgumentParser(description="Сборка portable-версии и установщика")
    ap.add_argument("--console", action="store_true", help="оставить окно консоли")
    ap.add_argument("--skip-installer", action="store_true")
    args = ap.parse_args()

    print("иконка...")
    make_icon()
    print("PyInstaller...")
    run_pyinstaller(args.console)
    print("portable-архив...")
    archive = make_portable()
    folder = os.path.join(DIST, APP)
    print(f"\nпапка      {folder}  ({size_of(folder) / 1e6:.0f} МБ)")
    print(f"portable   {archive}  ({size_of(archive) / 1e6:.0f} МБ)")
    if not args.skip_installer:
        print("установщик...")
        setup = make_installer()
        if setup and os.path.exists(setup):
            print(f"установщик {setup}  ({size_of(setup) / 1e6:.0f} МБ)")


if __name__ == "__main__":
    main()
