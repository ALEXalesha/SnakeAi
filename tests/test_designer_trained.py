"""Обученная сеть-дизайнер game/models/designer.npz: близко к раскладке кода, законы на свежих
размерах, паспорт честный, шум даёт живую вариацию."""
import json
import pathlib

import numpy as np
import pytest

from game.ai.models import load_designer
from game.design.designer_net import ROOM, SLOTS
from game.design.laws import check_layout
from game.train.design_train import Teacher, collect

MODELS = pathlib.Path(__file__).resolve().parents[1] / "game" / "models"
PASSPORT = json.loads((MODELS / "designer.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def teacher():
    t = Teacher()
    yield t
    t.w.close()


@pytest.fixture(scope="module")
def designer():
    return load_designer()


def test_passport_is_good_enough():
    f = PASSPORT["final"]
    assert f["px_mean"] < 1.5 and f["laws_pass"] >= 0.95
    assert len(PASSPORT["curve"]) >= 10 and PASSPORT["curve"][-1]["px"] < PASSPORT["curve"][0]["px"]


def test_fresh_sizes_obey_the_laws_and_match_the_code(teacher, designer):
    samples = collect(teacher, np.random.default_rng(77), 1)      # 2 языка x 5 шрифтов x 4 экрана
    ok, errs = 0, []
    for screen, w, h, lang, flags, z, code, size in samples:
        sc = teacher.state(lang, z[2], z, size, screen, flags)
        rects = designer.layout(screen, sc.width(), sc.height(), "dark", lang, flags, z)
        ok += not check_layout(sc, rects)
        for name, (x, y, ww, hh) in code.items():
            errs.append(np.abs(np.subtract(rects[name], (x - ROOM, y - ROOM, ww + 2 * ROOM, hh + 2 * ROOM))).mean())
    assert ok / len(samples) >= 0.9, ok / len(samples)
    assert np.mean(errs) < 2.0, np.mean(errs)


def test_noise_gives_a_living_variation(teacher, designer):
    a = designer.layout("settings", 1040, 720, "dark", "ru", (0, 0), np.array([-1.0, -1.0, 0.0, 0.0]))
    b = designer.layout("settings", 1040, 720, "dark", "ru", (0, 0), np.array([1.0, 1.0, 0.0, 0.0]))
    diff = np.mean([np.abs(np.subtract(a[n], b[n])).mean() for n in SLOTS["settings"]])
    assert diff > 4, diff
    sa = designer.style("dark", "ru", np.array([0, 0, 0, -1.0]))
    sb = designer.style("dark", "ru", np.array([0, 0, 0, 1.0]))
    assert sa["colors"]["accent"] != sb["colors"]["accent"]


def test_zero_noise_is_close_to_the_old_window(teacher, designer):
    z = np.zeros(4)
    for screen in SLOTS:
        sc = teacher.state("ru", 0.0, z, (1040, 720), screen)
        from game.design.layout import capture
        code = capture(sc)
        rects = designer.layout(screen, sc.width(), sc.height(), "dark", "ru", (0, 0), z)
        err = np.mean([np.abs(np.subtract(rects[n], code[n])).mean() for n in code])
        assert err < 3, (screen, err)
