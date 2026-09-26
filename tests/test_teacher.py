import numpy as np
import pytest

from teacher.rules import step
from world.cells import (BODY, DOWN, EMPTY, FOOD, HEAD, LEFT, NONE, RIGHT, UP, build,
                         chain, head, heading, length, tail)
from world.start import start_field


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def two(snake0, snake1, food=(), h=8, w=8):
    return build(h, w, [snake0, snake1], food)


S1_FAR = [(7, 7), (7, 6), (7, 5)]  # вторая змейка в углу, смотрит влево


def test_moves_forward_and_keeps_length(rng):
    f = two([(2, 1), (2, 2), (2, 3)], S1_FAR)
    out = step(f, NONE, NONE, rng)
    assert out.crashed == (False, False)
    assert chain(out.field, 0) == [(2, 2), (2, 3), (2, 4)]
    assert out.field[2, 1] == EMPTY


def test_turns_where_pressed(rng):
    f = two([(2, 1), (2, 2), (2, 3)], S1_FAR)
    out = step(f, UP, NONE, rng)
    assert head(out.field, 0) == (1, 3)
    assert out.field[2, 3] == BODY[0] + UP


def test_reverse_is_ignored(rng):
    f = two([(2, 1), (2, 2), (2, 3)], S1_FAR)
    out = step(f, LEFT, NONE, rng)
    assert head(out.field, 0) == (2, 4)


def test_wall_crash(rng):
    f = two([(2, 5), (2, 6), (2, 7)], [(7, 0), (7, 1), (7, 2)])
    out = step(f, NONE, NONE, rng)
    assert out.crashed == (True, False)
    assert out.field is None


def test_wall_crash_top(rng):
    f = two([(2, 3), (1, 3), (0, 3)], S1_FAR)
    assert step(f, UP, NONE, rng).crashed == (True, False)


def test_own_body_crash(rng):
    # змейка из 5 клеток загибается в себя
    f = two([(3, 1), (3, 2), (3, 3), (2, 3), (2, 2)], S1_FAR)
    out = step(f, DOWN, NONE, rng)
    assert out.crashed == (True, False)


def test_own_tail_is_a_crash_too(rng):
    # квадрат 2x2: голова идёт в клетку хвоста, хвост ещё на месте
    f = two([(3, 3), (3, 2), (2, 2), (2, 3)], S1_FAR)
    assert tail(f, 0) == (3, 3)
    assert step(f, DOWN, NONE, rng).crashed == (True, False)


def test_other_snake_body_crash(rng):
    f = two([(1, 1), (1, 2), (1, 3)], [(2, 2), (2, 3), (2, 4)])
    out = step(f, DOWN, NONE, rng)
    assert out.crashed == (True, False)


def test_head_to_head_same_cell_both_crash(rng):
    f = two([(3, 0), (3, 1), (3, 2)], [(3, 6), (3, 5), (3, 4)])
    assert step(f, NONE, NONE, rng).crashed == (True, True)


def test_heads_swapping_both_crash(rng):
    f = two([(3, 1), (3, 2), (3, 3)], [(3, 6), (3, 5), (3, 4)])
    assert step(f, NONE, NONE, rng).crashed == (True, True)


def test_eating_grows_and_places_food(rng):
    f = two([(2, 1), (2, 2), (2, 3)], S1_FAR, food=[(2, 4)])
    out = step(f, NONE, NONE, rng)
    assert out.ate == (True, False)
    assert chain(out.moved, 0) == [(2, 1), (2, 2), (2, 3), (2, 4)]
    assert (out.moved == FOOD).sum() == 0
    assert out.food is not None and out.field[out.food] == FOOD
    assert out.moved[out.food] == EMPTY


def test_second_snake_eats(rng):
    f = two([(0, 0), (0, 1), (0, 2)], [(5, 6), (5, 5), (5, 4)], food=[(5, 3)])
    out = step(f, RIGHT, NONE, rng)
    assert out.ate == (False, True)
    assert length(out.field, 1) == 4


def test_food_only_in_empty_cells():
    rng = np.random.default_rng(1)
    f = two([(2, 1), (2, 2), (2, 3)], [(6, 5), (6, 4), (6, 3)], food=[(2, 4)], h=7, w=6)
    seen = set()
    for _ in range(1000):
        out = step(f, NONE, NONE, rng)
        assert out.moved[out.food] == EMPTY
        seen.add(out.food)
    empties = int((out.moved == EMPTY).sum())
    assert len(seen) == empties  # все пустые клетки встречаются


def test_food_that_is_not_eaten_stays(rng):
    f = two([(2, 1), (2, 2), (2, 3)], S1_FAR, food=[(5, 1)])
    out = step(f, NONE, NONE, rng)
    assert out.ate == (False, False)
    assert out.food is None
    assert out.field[5, 1] == FOOD


def test_moving_into_cell_the_other_tail_leaves_is_a_crash(rng):
    # хвост второй змейки ещё на месте в начале хода - клетка занята
    f = two([(0, 3), (1, 3), (2, 3)], [(3, 3), (3, 4), (3, 5)])
    assert step(f, DOWN, NONE, rng).crashed == (True, False)


def test_pointers_lead_from_tail_to_head_after_many_steps(rng):
    f = start_field()
    moves = [UP, UP, RIGHT, RIGHT, DOWN, DOWN, RIGHT, RIGHT]
    for m in moves * 3:
        out = step(f, m, NONE, rng)
        assert out.field is not None
        f = out.field
        for s in (0, 1):
            assert chain(f, s) is not None


def test_start_field():
    f = start_field()
    assert f.shape == (32, 32)
    assert heading(f, 0) == RIGHT and heading(f, 1) == LEFT
    assert length(f, 0) == 3 and length(f, 1) == 3
    assert (f == FOOD).sum() == 1
    assert (f == HEAD[0]).sum() == 1 and (f == HEAD[1]).sum() == 1


@pytest.mark.parametrize("size", [8, 10, 16, 32])
def test_start_field_on_small_boards(size):
    f = start_field(size, size)
    for s in (0, 1):
        assert chain(f, s) is not None
