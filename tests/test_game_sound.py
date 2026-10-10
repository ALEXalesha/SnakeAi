import wave

import numpy as np
import pytest

from game.ui import sound

CASES = [
    (sound.eat, sound.EAT_MS),
    (sound.eat_net, sound.EAT_MS),
    (sound.crash, sound.CRASH_MS),
    (sound.beep, sound.BEEP_MS),
    (sound.go, sound.BEEP_MS),
    (sound.win, sound.WIN_MS),
    (sound.lose, sound.LOSE_MS),
]


@pytest.mark.parametrize("make,ms", CASES)
def test_sound_length_and_amplitude(make, ms):
    x = make()
    assert x.dtype == np.int16 and x.ndim == 1
    assert len(x) == int(sound.RATE * ms / 1000)
    peak = np.abs(x.astype(np.float64)).max() / 32767
    assert 0.2 <= peak <= 1.0                      # слышно и без перегруза
    assert abs(int(x[-1])) < 0.02 * 32767          # конец без щелчка


def dominant_hz(x):
    spec = np.abs(np.fft.rfft(x.astype(np.float64)))
    return np.fft.rfftfreq(len(x), 1 / sound.RATE)[int(spec.argmax())]


def test_last_countdown_beep_is_higher():
    assert dominant_hz(sound.go()) > dominant_hz(sound.beep()) * 1.5


def test_net_eats_lower_than_player():
    assert dominant_hz(sound.eat_net()) < dominant_hz(sound.eat())


def test_win_goes_up_and_lose_goes_down():
    w, l = sound.win(), sound.lose()
    assert dominant_hz(w[-len(w) // 4:]) > dominant_hz(w[:len(w) // 4])
    assert dominant_hz(l[-len(l) // 4:]) < dominant_hz(l[:len(l) // 4])


def test_write_wav(tmp_path):
    x = sound.eat()
    path = sound.write_wav(tmp_path / "eat.wav", x)
    with wave.open(str(path), "rb") as f:
        assert f.getframerate() == sound.RATE and f.getnchannels() == 1
        assert f.getsampwidth() == 2 and f.getnframes() == len(x)


def test_silent_player_does_nothing_quietly():
    s = sound.Sounds(enabled=False)
    s.set_volume(30)
    for ev in ("eat0", "eat1", "crash", "countdown", "go", "win", "lose", "round_win", "чужое"):
        s.on_event(ev)


def test_real_player_never_raises():
    from qt_app import qapp
    qapp()
    s = sound.Sounds(volume=0)       # есть звуковая карта или нет - не падает
    s.on_event("eat0")
    s.set_volume(0)
