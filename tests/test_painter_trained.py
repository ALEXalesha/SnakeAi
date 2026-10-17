"""Обученная сеть-художник game/models/painter.npz: законы на свежих шумах, паспорт честный,
«рука» живая, но узнаваемо та же."""
import json
import pathlib

import numpy as np
import pytest

from game.ai.models import load_painter
from game.design.laws import check_tiles
from game.design.tiles import code_tiles, common_keys, group
from qt_app import qapp

MODELS = pathlib.Path(__file__).resolve().parents[1] / "game" / "models"
PASSPORT = json.loads((MODELS / "painter.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def painter():
    qapp()
    return load_painter()


def diff(a, b):
    return np.abs(a.astype(np.float32) - b).reshape(len(a), -1).mean(1) / 255


def test_laws_hold_on_fresh_noise_for_every_palette(painter):
    rng = np.random.default_rng(2026)
    keys = common_keys()
    kinds = [group(k) for k in keys]
    for pal in range(3):
        for _ in range(7):
            z = rng.uniform(-1, 1, 4)
            drawn = painter.draw(keys, pal, z)
            assert check_tiles(drawn, code_tiles(keys, pal, z), kinds, PASSPORT["limit"]) == [], (pal, z)


def test_passport_matches_a_fresh_measurement(painter):
    rng = np.random.default_rng(5)
    keys = common_keys()
    d = np.concatenate([diff(painter.draw(keys, pal, z), code_tiles(keys, pal, z))
                        for pal in range(3) for z in (rng.uniform(-1, 1, 4) for _ in range(3))])
    f = PASSPORT["final"]
    assert d.mean() == pytest.approx(f["diff_mean"], rel=0.35)
    assert f["laws_pass"] == 1.0 and f["diff_max"] < PASSPORT["limit"] <= 0.04
    assert len(PASSPORT["curve"]) >= 10 and PASSPORT["curve"][-1]["diff"] < PASSPORT["curve"][0]["diff"]


def test_the_hand_is_alive_but_recognisable(painter):
    keys = common_keys()
    a = painter.draw(keys, 0, np.full(4, -1.0))
    b = painter.draw(keys, 0, np.full(4, 1.0))
    assert diff(a, b).mean() > 0.01                       # разный шум - заметно разная рука
    zero = painter.draw(keys, 0, np.zeros(4))
    assert diff(zero, code_tiles(keys, 0, np.zeros(4))).max() < PASSPORT["limit"]


def test_broken_snake_tiles_stay_close_or_fall_back(painter):
    """Ключей разорванной змейки (три связи, тело без связей) в обучении нет - тайл сети
    либо близок к кодовому, либо игра берёт кодовый (AiTiles проверяет поштучно)."""
    from game.design.journal import Journal
    from game.design.runtime import AiTiles
    from game.design.tiles import BODY, encode
    odd = [encode(BODY, 0, 0b0111, 3, 0), encode(BODY, 1, 0, 7, 1), encode(BODY, 0, 0b1111, 5, 0)]
    j = Journal()
    src = AiTiles(painter, j, np.random.default_rng(0), PASSPORT["limit"])
    got = src.tiles(0, odd)
    code = code_tiles(odd, 0, src._z_of[0])
    for k, c in zip(odd, code):
        assert diff(got[k][None], c[None])[0] <= PASSPORT["limit"]
    assert j.data["tile_sets"] == 1
