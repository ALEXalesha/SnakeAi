import os
import pathlib
import sys

from game import paths

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_data_in_local_appdata(tmp_path):
    got = paths.data_dir(exe_folder=tmp_path / "prog", environ={"LOCALAPPDATA": str(tmp_path / "la")})
    assert pathlib.Path(got) == tmp_path / "la" / "SnakeAIGame"


def test_portable_keeps_saves_beside_exe(tmp_path):
    (tmp_path / "portable.txt").write_text("", encoding="utf-8")
    got = paths.data_dir(exe_folder=tmp_path, environ={"LOCALAPPDATA": str(tmp_path / "la")})
    assert pathlib.Path(got) == tmp_path / "saves"


def test_no_localappdata_falls_back_to_home(tmp_path):
    got = paths.data_dir(exe_folder=tmp_path, environ={})
    assert pathlib.Path(got) == pathlib.Path(os.path.expanduser("~")) / "SnakeAIGame"


def test_models_from_source_and_from_bundle(monkeypatch, tmp_path):
    assert pathlib.Path(paths.models_dir()) == ROOT / "models"
    assert pathlib.Path(paths.exe_dir()) == ROOT
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "SnakeAIGame.exe"))
    assert pathlib.Path(paths.models_dir()) == tmp_path / "bundle" / "models"
    assert pathlib.Path(paths.exe_dir()) == tmp_path / "dist"
