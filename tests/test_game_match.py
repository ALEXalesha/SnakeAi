import numpy as np

from game import match as M
from qt_app import Const, RulesWorld, Steady
from world.cells import DOWN, HEAD, LEFT, NONE, RIGHT, UP
from world.net import Result


def new_match(world=None, opponent=None, target=3, speed=100):
    return M.Match(world or RulesWorld(), opponent or Const(DOWN), np.random.default_rng(0),
                   target=target, speed_ms=speed)


def skip_countdown(m):
    m.update(M.COUNT_STEP_MS * 3)
    assert m.phase == M.PLAYING


def play_round(m, guard=500):
    """Ходы до конца раунда."""
    skip_countdown(m)
    for _ in range(guard):
        if m.phase != M.PLAYING:
            return
        m.update(m.speed_ms)
    raise AssertionError("раунд не кончился")


def test_countdown_three_two_one_then_play():
    world = RulesWorld()
    m = new_match(world)
    assert m.phase == M.COUNTDOWN and m.count == 3
    assert m.take_events() == ["countdown"]
    m.update(M.COUNT_STEP_MS - 1)
    assert m.count == 3 and m.take_events() == []
    m.update(1)
    assert m.count == 2 and m.take_events() == ["countdown"]
    m.update(M.COUNT_STEP_MS)
    assert m.count == 1 and m.take_events() == ["countdown"]
    m.update(M.COUNT_STEP_MS)
    assert m.phase == M.PLAYING and m.take_events() == ["go"]
    assert world.calls == []          # во время отсчёта мир не ходит


def test_world_moves_once_per_speed():
    world = RulesWorld()
    m = new_match(world, speed=110)
    skip_countdown(m)
    m.update(109)
    assert world.calls == []
    m.update(1)
    assert len(world.calls) == 1
    m.update(330)
    assert len(world.calls) == 4


def test_player_wins_match_to_three():
    m = new_match(opponent=Const(DOWN))         # сеть едет вниз в стену
    for rnd in (1, 2, 3):
        assert m.round == rnd
        play_round(m)
        assert m.crashed == (False, True)
        assert m.round_result == "win"
        assert m.score == [rnd, 0]
        if rnd < 3:
            assert m.phase == M.ROUND_OVER
            m.update(M.ROUND_PAUSE_MS - 1)
            assert m.phase == M.ROUND_OVER
            m.update(1)
            assert m.phase == M.COUNTDOWN
    assert m.phase == M.MATCH_OVER and m.winner == 0
    events = m.take_events()
    assert events.count("round_win") == 3 and events[-1] == "win"
    m.update(10_000)
    assert m.phase == M.MATCH_OVER and m.round == 3


def test_player_loses_match():
    m = new_match(opponent=Steady(), target=2)
    for _ in range(2):
        skip_countdown(m)
        m.press(UP)                              # игрок вверх, в стену
        while m.phase == M.PLAYING:
            m.update(m.speed_ms)
        if m.phase == M.ROUND_OVER:
            m.update(M.ROUND_PAUSE_MS)
    assert m.score == [0, 2] and m.winner == 1
    assert m.take_events()[-1] == "lose"


def test_both_crash_is_draw_without_point():
    # Обе змейки едут прямо навстречу краям и врезаются на одном ходу.
    m = new_match(opponent=Steady())
    play_round(m)
    assert m.crashed == (True, True)
    assert m.round_result == "draw"
    assert m.score == [0, 0]
    assert m.phase == M.ROUND_OVER
    assert "round_draw" in m.take_events()


def test_key_queue_keeps_two_presses():
    world = RulesWorld()
    m = new_match(world)
    m.press(UP)
    m.press(LEFT)
    m.press(DOWN)                                # третье не влезает
    assert list(m.keys) == [UP, LEFT]
    skip_countdown(m)
    for _ in range(3):
        m.update(m.speed_ms)
    assert [a0 for a0, _ in world.calls] == [UP, LEFT, NONE]


def test_repeat_of_same_key_takes_one_place():
    m = new_match()
    m.press(UP)
    m.press(UP)
    m.press(LEFT)
    assert list(m.keys) == [UP, LEFT]


def test_reverse_goes_to_network_as_is():
    world = RulesWorld()
    m = new_match(world)
    skip_countdown(m)
    m.press(LEFT)                                # игрок смотрит вправо: это разворот
    m.update(m.speed_ms)
    assert world.calls[0][0] == LEFT


class ScriptWorld:
    """Мир, который отдаёт заранее заданные ответы."""

    def __init__(self, answers):
        self.answers = list(answers)

    def step(self, field, a0, a1, rng):
        make = self.answers.pop(0)
        return make(field)


def result(field, ate=(False, False), crashed=(False, False)):
    return Result(field, ate, crashed, None, np.full(field.shape, 1 / field.size), 0.5)


def without_head(s):
    def make(field):
        f = field.copy()
        f[f == HEAD[s]] = 0
        return result(f)
    return make


def test_network_glitch_without_head_counts_as_crash():
    m = new_match(ScriptWorld([without_head(1)]), Const(RIGHT))
    skip_countdown(m)
    m.update(m.speed_ms)
    assert m.phase == M.ROUND_OVER
    assert m.crashed == (False, True) and m.score == [1, 0]
    m.update(M.ROUND_PAUSE_MS)
    assert m.phase == M.COUNTDOWN and m.round == 2


def test_network_glitch_both_heads_lost_is_draw():
    def both(field):
        f = field.copy()
        f[(f == HEAD[0]) | (f == HEAD[1])] = 0
        return result(f)
    m = new_match(ScriptWorld([both]), Const(RIGHT))
    skip_countdown(m)
    m.update(m.speed_ms)
    assert m.crashed == (True, True) and m.score == [0, 0]


def test_eat_events_lengths_and_confidence():
    m = new_match(ScriptWorld([lambda f: result(f.copy(), ate=(True, False)),
                               lambda f: result(f.copy(), ate=(False, True))]))
    assert m.lengths() == (3, 3)
    m.take_events()
    skip_countdown(m)
    m.take_events()
    m.update(m.speed_ms)
    m.update(m.speed_ms)
    assert m.take_events() == ["eat0", "eat1"]
    assert m.eaten == [1, 1]
    assert m.confidence == 0.5 and m.food_probs.shape == (32, 32)


def test_pause_stops_time_and_keys():
    world = RulesWorld()
    m = new_match(world)
    skip_countdown(m)
    m.paused = True
    m.update(5000)
    m.press(UP)
    assert world.calls == [] and list(m.keys) == []
    m.paused = False
    m.update(m.speed_ms)
    assert len(world.calls) == 1


def test_longest_snake_is_tracked():
    m = new_match(opponent=Const(DOWN))
    play_round(m)
    assert m.longest[0] >= 3
