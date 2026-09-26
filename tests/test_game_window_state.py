import json

from PySide6.QtWidgets import QMainWindow

from game import window_state as ws
from qt_app import qapp

PRIMARY = {"x": 0, "y": 0, "width": 1920, "height": 1040}
SECOND = {"x": 1920, "y": 0, "width": 1280, "height": 984}
OPTS = {"width": 1040, "height": 720, "minWidth": 820, "minHeight": 600}


def test_normal_case_keeps_place_and_size():
    saved = {"x": 2100, "y": 50, "width": 1100, "height": 760, "maximized": False}
    assert ws.restore(saved, [PRIMARY, SECOND], OPTS) == saved


def test_monitor_gone_lets_windows_choose():
    saved = {"x": 2100, "y": 50, "width": 1100, "height": 760, "maximized": True}
    got = ws.restore(saved, [PRIMARY], OPTS)
    assert "x" not in got and "y" not in got
    assert (got["width"], got["height"], got["maximized"]) == (1100, 760, True)


def test_title_off_screen_lets_windows_choose():
    for y in (-500, -37, 1100):                    # от заголовка на экране 1 строка или ничего
        got = ws.restore({"x": 100, "y": y, "width": 1040, "height": 720}, [PRIMARY], OPTS)
        assert "x" not in got, y


def test_partly_visible_title_is_pulled_in_and_size_limited():
    got = ws.restore({"x": 1700, "y": 900, "width": 3000, "height": 500}, [PRIMARY], OPTS)
    assert got["width"] == 1920 and got["height"] == 600          # не больше экрана, не меньше минимума
    assert got["x"] == 0 and got["y"] == 1040 - 600


def test_garbage_gives_default():
    for saved in (None, [], "x", {"width": "a"}, {"width": float("nan"), "height": 5}):
        assert ws.restore(saved, [PRIMARY], OPTS) == {"width": 1040, "height": 720,
                                                      "maximized": False}


def test_screen_areas_from_qt():
    qapp()
    areas = ws.screen_areas()
    assert areas and all(a["width"] > 0 and a["height"] > 0 for a in areas)


def test_remember_puts_window_and_saves_it(tmp_path):
    qapp()
    path = tmp_path / "window.json"
    area = ws.screen_areas()[0]
    x, y = area["x"] + 10, area["y"] + 20
    path.write_text(json.dumps({"x": x, "y": y, "width": 700, "height": 500}), encoding="utf-8")
    win = QMainWindow()
    rem = ws.Remember(win, path, {"width": 640, "height": 480, "minWidth": 300, "minHeight": 200})
    assert (win.width(), win.height()) == (700, 500)
    assert (win.x(), win.y()) == (x, y)
    win.resize(650, 450)
    rem.track()
    assert rem.save()
    back = json.loads(path.read_text(encoding="utf-8"))
    assert (back["width"], back["height"], back["maximized"]) == (650, 450, False)
    win.close()


def test_broken_window_file_is_ignored(tmp_path):
    qapp()
    path = tmp_path / "window.json"
    path.write_text("{битый", encoding="utf-8")
    win = QMainWindow()
    ws.Remember(win, path, {"width": 640, "height": 480, "minWidth": 300, "minHeight": 200})
    assert (win.width(), win.height()) == (640, 480)
    win.close()
