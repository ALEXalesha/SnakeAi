"""Обученные соперники из models/: уровни различаются, сеть сама не лезет в стену."""
import json
import pathlib

import numpy as np
import pytest

from game.ai.player_net import PlayerNet
from game.train.player_train import Bot, Random, evaluate

MODELS = pathlib.Path(__file__).resolve().parents[1] / "game" / "models"
LEVELS = ("novice", "medium", "strong")


@pytest.fixture(scope="module")
def nets():
    return {k: PlayerNet.load(MODELS / f"player_{k}.npz") for k in LEVELS}


@pytest.fixture(scope="module")
def passport():
    return json.loads((MODELS / "player.json").read_text(encoding="utf-8"))


def test_passport_has_all_levels_and_curves(passport):
    assert set(passport["levels"]) == set(LEVELS)
    assert passport["imitation_curve"] and passport["rl_curve"]


def test_levels_are_ordered_against_the_bot(passport):
    """«Новичок» проигрывает боту чаще всех, «сильный» - не чаще «среднего»."""
    lv = passport["levels"]
    score = {k: lv[k]["vs_bot"]["win"] - lv[k]["vs_bot"]["loss"] for k in LEVELS}
    assert score["novice"] < score["medium"] <= score["strong"], score


def test_every_level_beats_a_random_snake(nets):
    for k, net in nets.items():
        r = evaluate(net, Random(np.random.default_rng(1)), np.random.default_rng(2), 20)
        assert r["win"] >= 0.85, (k, r)


def test_strong_level_survives_against_the_bot(nets):
    r = evaluate(nets["strong"], Bot(), np.random.default_rng(3), 20)
    assert r["loss"] <= 0.5, r


def test_imitation_learned_the_bot(passport):
    assert passport["imitation_curve"][-1]["accuracy"] >= 0.9
