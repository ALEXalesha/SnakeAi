import main


def test_selftest_plays_real_networks_and_reports(tmp_path):
    out = tmp_path / "итог.txt"
    assert main.selftest(str(out), max_steps=300) == 0
    text = out.read_text(encoding="utf-8")
    assert "ИТОГ: работает" in text
    assert "ходов" in text and "уверенность" in text
