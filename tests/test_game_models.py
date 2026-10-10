import json
import sys
import types

import numpy as np
import pytest

from game.ai import models
from game.ai.world_net import WorldNet


def test_missing_world_model_says_where(tmp_path):
    with pytest.raises(models.ModelMissing) as err:
        models.load_world(tmp_path)
    assert "world.npz" in str(err.value)


def test_world_model_loads(tmp_path):
    WorldNet(hidden=8, glob=4, rng=np.random.default_rng(2)).save(tmp_path / "world.npz")
    net = models.load_world(tmp_path)
    assert isinstance(net, WorldNet) and net.hidden == 8


def test_broken_world_model_is_a_message_not_a_crash(tmp_path):
    (tmp_path / "world.npz").write_bytes(b"not a zip")
    with pytest.raises(models.ModelMissing):
        models.load_world(tmp_path)


def test_opponent_missing_file_and_unknown_level(tmp_path):
    with pytest.raises(models.ModelMissing) as err:
        models.load_opponent("medium", tmp_path)
    assert "player_medium.npz" in str(err.value)
    with pytest.raises(models.ModelMissing):
        models.load_opponent("бог", tmp_path)


def test_opponent_loads_through_player_net(tmp_path, monkeypatch):
    class PlayerNet:
        @classmethod
        def load(cls, path):
            obj = cls()
            obj.path = path
            return obj

    fake = types.ModuleType("game.ai.player_net")
    fake.PlayerNet = PlayerNet
    monkeypatch.setitem(sys.modules, "game.ai.player_net", fake)
    (tmp_path / "player_strong.npz").write_bytes(b"")
    net = models.load_opponent("strong", tmp_path)
    assert str(net.path).endswith("player_strong.npz")


def test_passports(tmp_path):
    assert models.load_passport("world", tmp_path) is None
    (tmp_path / "world.json").write_text(json.dumps({"final": {"field": 0.99}}), encoding="utf-8")
    assert models.load_passport("world", tmp_path) == {"final": {"field": 0.99}}
    (tmp_path / "player.json").write_text("{битый", encoding="utf-8")
    assert models.load_passport("player", tmp_path) is None
    (tmp_path / "player.json").write_text("[1]", encoding="utf-8")
    assert models.load_passport("player", tmp_path) is None


def test_loader_object_uses_its_folder(tmp_path):
    loader = models.Models(tmp_path)
    with pytest.raises(models.ModelMissing):
        loader.load_world()
    assert loader.load_passport("world") is None
