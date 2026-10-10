import numpy as np
import pytest

from game.ai.bot import bot_move, flood
from game.ai.player_net import PlayerNet
from game.ai.view import SIZE, VIEW_LEN, view
from game.teacher.data import random_field
from game.teacher.rules import step
from game.core.cells import DELTA, DOWN, EMPTY, FOOD, LEFT, RIGHT, UP, build, head, heading


def planes(v):
    return v[:SIZE * SIZE * 4].reshape(SIZE, SIZE, 4)


def test_view_length_and_centre():
    f = build(32, 32, [[(10, 10), (10, 11)], [(20, 20), (20, 21)]], food=[(5, 11)])
    v = view(f, 0)
    assert v.shape == (VIEW_LEN,) and v.dtype == np.float32
    p = planes(v)
    c = SIZE // 2
    assert p[c, c, 0] == 1            # своя голова - препятствие
    assert p[c, c - 1, 3] == 1        # шея слева
    assert p[c - 5, c, 1] == 1        # еда на 5 клеток выше


def test_view_marks_outside_as_obstacle():
    f = build(32, 32, [[(0, 1), (0, 0)], [(20, 20), (20, 21)]])
    p = planes(view(f, 0))
    c = SIZE // 2
    assert p[c - 1, c, 0] == 1 and p[c, c - 1, 0] == 1   # над и слева - край
    assert p[c + 1, c, 0] == 0                           # снизу пусто


def test_view_food_vector_and_heading():
    f = build(32, 32, [[(10, 10), (10, 11)], [(20, 20), (20, 21)]], food=[(30, 1)])
    v = view(f, 0)
    np.testing.assert_allclose(v[SIZE * SIZE * 4:SIZE * SIZE * 4 + 2], [20 / 32, -10 / 32])
    assert list(v[-4:]) == [0, 0, 0, 1]    # смотрит вправо


def test_view_is_symmetric_between_snakes():
    """Для змейки 1 «своя» и «чужая» меняются местами - сеть одна на обе стороны."""
    f = build(32, 32, [[(10, 10), (10, 11)], [(20, 20), (20, 21)]], food=[(5, 5)])
    g = build(32, 32, [[(20, 20), (20, 21)], [(10, 10), (10, 11)]], food=[(5, 5)])
    np.testing.assert_array_equal(view(f, 0), view(g, 1))


def test_view_sees_other_head():
    f = build(32, 32, [[(10, 10), (10, 11)], [(12, 14), (12, 13)]])
    p = planes(view(f, 0))
    c = SIZE // 2
    assert p[c + 2, c + 2, 2] == 1


def test_bot_goes_to_food_by_shortest_path():
    f = build(20, 20, [[(10, 2), (10, 3), (10, 4)], [(19, 19), (19, 18)]], food=[(4, 4)])
    assert bot_move(f, 0) == UP
    f = build(20, 20, [[(10, 2), (10, 3), (10, 4)], [(19, 19), (19, 18)]], food=[(10, 9)])
    assert bot_move(f, 0) == RIGHT


def test_bot_goes_around_a_wall_of_body():
    # еда прямо над головой, но за телом второй змейки от левого края до столбца 11 -
    # обход только справа
    wall = [(9, c) for c in range(0, 12)]
    f = build(20, 20, [[(12, 5), (11, 5), (10, 5)], wall], food=[(6, 5)])
    assert bot_move(f, 0) == RIGHT


def test_bot_avoids_a_dead_end():
    # еда в кармане слева из 2 клеток, а змейка длины 4 туда не поместится
    snake0 = [(0, 3), (0, 2), (0, 1), (1, 1)]      # голова (1,1), смотрит вниз
    snake1 = [(2, 0), (3, 0), (4, 0), (5, 0)]      # хвост (2,0) закрывает карман снизу
    f = build(6, 6, [snake0, snake1], food=[(0, 0)])
    assert flood(f, (1, 0)) == 2
    assert bot_move(f, 0) in (DOWN, RIGHT)


def safe_moves(f, s):
    H, W = f.shape
    h = head(f, s)
    out = []
    for d in range(4):
        t = (h[0] + DELTA[d][0], h[1] + DELTA[d][1])
        if 0 <= t[0] < H and 0 <= t[1] < W and f[t] in (EMPTY, FOOD):
            out.append(d)
    return out


def test_bot_never_steps_into_death_when_a_safe_move_exists():
    rng = np.random.default_rng(4)
    for _ in range(400):
        f = random_field(rng, 16, 16)
        for s in (0, 1):
            safe = safe_moves(f, s)
            if safe:
                assert bot_move(f, s) in safe


def test_flood_counts_reachable_cells():
    f = build(5, 5, [[(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)], []])
    assert flood(f, (0, 0)) == 10
    assert flood(f, (4, 4)) == 10


def test_player_net_acts_and_round_trips(tmp_path):
    net = PlayerNet(rng=np.random.default_rng(0))
    f = build(32, 32, [[(10, 10), (10, 11)], [(20, 20), (20, 21)]], food=[(5, 5)])
    a = net.act(f, 0)
    assert a in (UP, DOWN, LEFT, RIGHT)
    net.save(tmp_path / "p.npz")
    back = PlayerNet.load(tmp_path / "p.npz")
    np.testing.assert_array_equal(net.logits(view(f, 0)[None]), back.logits(view(f, 0)[None]))


def test_bot_plays_long_rounds_against_itself():
    rng = np.random.default_rng(0)
    from game.core.start import start_field
    lengths = []
    for _ in range(3):
        f = start_field()
        for t in range(400):
            o = step(f, bot_move(f, 0), bot_move(f, 1), rng)
            if o.field is None:
                break
            f = o.field
        lengths.append(t)
    assert np.mean(lengths) > 100


def test_bot_does_not_walk_into_a_head_on_collision():
    # между головами одна клетка: шагнуть туда - обе врежутся, если другая тоже шагнёт
    f = build(12, 12, [[(5, 1), (5, 2), (5, 3)], [(5, 7), (5, 6), (5, 5)]], food=[(5, 4)])
    assert bot_move(f, 0) in (UP, DOWN)
