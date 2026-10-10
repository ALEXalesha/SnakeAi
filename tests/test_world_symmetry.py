import numpy as np
import pytest

from game.teacher.data import greedy_move, random_field
from game.teacher.rules import step
from game.core.cells import DOWN, LEFT, NONE, RIGHT, UP, build
from game.ai.world_net import WorldNet
from game.core.symmetry import TRANSFORMS, VIEWS, action, apply, class_map, direction_perm, undo


def test_quarter_turn_renames_directions():
    # np.rot90 поворачивает против часовой: верх уходит влево
    assert direction_perm(1, False) == (LEFT, RIGHT, DOWN, UP)


def test_mirror_swaps_left_and_right():
    assert direction_perm(0, True) == (UP, DOWN, RIGHT, LEFT)


def test_identity_changes_nothing():
    assert direction_perm(0, False) == (UP, DOWN, LEFT, RIGHT)
    assert list(class_map(direction_perm(0, False))) == list(range(12))


@pytest.mark.parametrize("k, flip", TRANSFORMS)
def test_undo_reverts_apply(k, flip):
    a = np.arange(5 * 7).reshape(5, 7)
    np.testing.assert_array_equal(undo(apply(a, k, flip), k, flip), a)


def test_eight_views_are_distinct():
    a = np.arange(16).reshape(4, 4)
    seen = {apply(a, k, f).tobytes() for k, f in TRANSFORMS}
    assert len(seen) == 8


def test_rules_do_not_change_under_symmetry():
    """То, на чём держится усреднение: повернуть поле и ход - то же, что повернуть итог."""
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(150):
        f = random_field(rng, 9, 11)
        a0, a1 = int(rng.integers(0, 5)), int(rng.integers(0, 5))
        base = step(f, a0, a1, np.random.default_rng(1))
        for k, flip, perm, cm in VIEWS:
            g = cm[apply(f, k, flip)]
            o = step(g, action(a0, perm), action(a1, perm), np.random.default_rng(1))
            assert o.crashed == base.crashed and o.ate == base.ate
            if base.moved is not None:
                np.testing.assert_array_equal(o.moved, cm[apply(base.moved, k, flip)])
                checked += 1
    assert checked > 300


def test_symmetric_prediction_is_itself_symmetric():
    net = WorldNet(hidden=8, glob=4, rng=np.random.default_rng(2))
    f = build(10, 10, [[(2, 1), (2, 2), (2, 3)], [(7, 8), (7, 7), (7, 6)]], food=[(5, 5)])
    cells, ev, _, food = net.predict(f, UP, NONE)
    for k, flip, perm, cm in VIEWS:
        c2, ev2, _, food2 = net.predict(cm[apply(f, k, flip)], action(UP, perm), action(NONE, perm))
        np.testing.assert_array_equal(c2, cm[apply(cells, k, flip)])
        np.testing.assert_array_equal(ev2, ev)
        np.testing.assert_allclose(food2, apply(food, k, flip), atol=1e-9)


def test_single_pass_is_still_available():
    net = WorldNet(hidden=8, glob=4)
    f = build(8, 8, [[(2, 1), (2, 2), (2, 3)], [(6, 6), (6, 5), (6, 4)]])
    one = net.predict(f, NONE, NONE, symmetric=False)
    assert one[0].shape == (8, 8)
