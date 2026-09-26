import numpy as np

from teacher.data import CHANGE_WEIGHT, SNAKE_WEIGHT, Sample, play, random_field, tensors
from world.cells import EMPTY, FOOD, NONE, build, chain, tail


def sample(field, a0=NONE, a1=NONE):
    from teacher.rules import step
    o = step(field, a0, a1, np.random.default_rng(0))
    moved = field.copy() if o.field is None else o.moved
    food = -1 if o.food is None else o.food[0] * field.shape[1] + o.food[1]
    return Sample(field, a0, a1, moved, np.array([*o.ate, *o.crashed], np.float32), food)


def test_changed_cells_and_neighbours_weigh_more():
    f = build(8, 8, [[(2, 1), (2, 2), (2, 3)], [(6, 6), (6, 5), (6, 4)]])
    _, _, w, *_ = tensors([sample(f)])
    assert w[0, 2, 4] == CHANGE_WEIGHT      # новая голова
    assert w[0, 2, 1] == CHANGE_WEIGHT      # исчезнувший хвост
    assert w[0, 0, 7] == 1.0                # далёкая пустая клетка


def test_snake_cells_weigh_more_than_empty():
    f = build(12, 12, [[(2, 1), (2, 2), (2, 3), (3, 3), (4, 3), (4, 4), (4, 5)], [(10, 10), (10, 9), (10, 8)]])
    _, _, w, *_ = tensors([sample(f)])
    assert w[0, 3, 3] == SNAKE_WEIGHT       # середина тела, далеко от изменений
    assert w[0, 8, 1] == 1.0


def test_tail_weighs_more_even_when_it_stays():
    """Хвост съевшей змейки не меняется, но правило «хвост остаётся» - самое редкое и
    единственное дальнее: без веса сеть его не выучивает (замер 26.09: половина ошибок)."""
    f = build(12, 12, [[(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6)], [(10, 10), (10, 9), (10, 8)]],
              food=[(2, 7)])
    s = sample(f)
    assert s.events[0] == 1
    _, _, w, *_ = tensors([s])
    assert tail(f, 0) == (2, 1)
    assert s.moved[2, 1] != EMPTY
    assert w[0, 2, 1] == CHANGE_WEIGHT


def test_crash_steps_do_not_teach_the_field():
    f = build(8, 8, [[(2, 5), (2, 6), (2, 7)], [(6, 6), (6, 5), (6, 4)]])
    s = sample(f)
    assert s.events[2] == 1
    _, _, w, events, ev_w, _, food_mask = tensors([s])
    assert w.sum() == 0
    assert ev_w[0, 0] == 0 and ev_w[0, 1] == 0 and ev_w[0, 2] == 1
    assert food_mask[0] == 0


def test_played_samples_are_consistent():
    rng = np.random.default_rng(2)
    for s in play(rng, 10, 10, 300):
        crash = s.events[2:].max() > 0
        assert chain(s.field, 0) is not None and chain(s.field, 1) is not None
        if not crash:
            assert chain(s.moved, 0) is not None and chain(s.moved, 1) is not None
            assert (s.food >= 0) == bool(s.events[:2].max())


def test_random_fields_have_both_snakes():
    rng = np.random.default_rng(5)
    for _ in range(50):
        f = random_field(rng, 12, 12)
        assert chain(f, 0) is not None and chain(f, 1) is not None
        assert (f == FOOD).sum() <= 2
