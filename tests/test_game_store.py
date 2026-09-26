import json

import pytest

from game import store


def test_settings_defaults_without_file(tmp_path):
    s = store.load_settings(tmp_path / "settings.json")
    assert s == {"speed_ms": 110, "opponent": "medium", "volume": 60, "palette": 0,
                 "show_food_map": False}


def test_settings_round_trip(tmp_path):
    path = tmp_path / "deep" / "settings.json"
    s = {"speed_ms": 200, "opponent": "strong", "volume": 15, "palette": 2, "show_food_map": True}
    store.save_settings(path, s)
    assert store.load_settings(path) == s
    assert not list(path.parent.glob("*.tmp"))      # временный файл не остался


@pytest.mark.parametrize("text", ["{не json", "[1, 2, 3]", "", "null", '"строка"'])
def test_broken_or_foreign_settings_give_defaults(tmp_path, text):
    path = tmp_path / "settings.json"
    path.write_text(text, encoding="utf-8")
    assert store.load_settings(path) == store.DEFAULT_SETTINGS


def test_settings_are_clipped_and_checked(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"speed_ms": 5, "opponent": "бог", "volume": 150, "palette": 7,
                                "show_food_map": "да", "лишнее": 1}), encoding="utf-8")
    assert store.load_settings(path) == {"speed_ms": 60, "opponent": "medium", "volume": 100,
                                         "palette": 2, "show_food_map": False}
    path.write_text(json.dumps({"speed_ms": 999, "volume": -3, "palette": -1,
                                "opponent": "novice"}), encoding="utf-8")
    s = store.load_settings(path)
    assert (s["speed_ms"], s["volume"], s["palette"], s["opponent"]) == (250, 0, 0, "novice")
    path.write_text(json.dumps({"speed_ms": True, "volume": "громко", "palette": 1.6}),
                    encoding="utf-8")
    s = store.load_settings(path)
    assert (s["speed_ms"], s["volume"], s["palette"]) == (110, 60, 2)


def test_stats_round_trip_and_records(tmp_path):
    path = tmp_path / "stats.json"
    st = store.load_stats(path)
    assert st["matches"] == 0 and st["levels"]["strong"]["wins"] == 0
    store.record_round(st, "medium", "win", player_length=7, food=4)
    store.record_round(st, "medium", "draw", player_length=12, food=1)
    store.record_round(st, "strong", "lose", player_length=5, food=0)
    store.record_match(st, "medium", won=True)
    store.record_match(st, "strong", won=False)
    store.save_stats(path, st)
    back = store.load_stats(path)
    assert back == st
    assert back["rounds"] == 3 and back["matches"] == 2
    assert back["longest"] == 12 and back["food"] == 5
    lv = back["levels"]["medium"]
    assert (lv["wins"], lv["losses"], lv["draws"], lv["match_wins"]) == (1, 0, 1, 1)
    assert back["levels"]["strong"]["match_losses"] == 1


def test_broken_stats_give_zeros(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text("{обрыв", encoding="utf-8")
    assert store.load_stats(path) == store.empty_stats()
    path.write_text(json.dumps({"matches": -4, "rounds": "много", "longest": 9,
                                "levels": {"medium": {"wins": 3, "losses": -1}, "чужой": {}}}),
                    encoding="utf-8")
    st = store.load_stats(path)
    assert st["matches"] == 0 and st["rounds"] == 0 and st["longest"] == 9
    assert st["levels"]["medium"]["wins"] == 3 and st["levels"]["medium"]["losses"] == 0
    assert set(st["levels"]) == set(store.LEVELS)


def test_store_saves_each_change_at_once(tmp_path):
    s = store.Store(tmp_path)
    s.set("speed_ms", 180)
    s.set("volume", 400)
    again = store.Store(tmp_path)
    assert again.settings["speed_ms"] == 180 and again.settings["volume"] == 100
    s.stats["food"] = 3
    s.save_stats()
    assert store.Store(tmp_path).stats["food"] == 3
