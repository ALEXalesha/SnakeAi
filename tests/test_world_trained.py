"""Обученная сеть-мир из models/world.npz против учителя на отложенных данных 32x32."""
import pathlib

import numpy as np
import pytest

from teacher.data import grow, greedy_move, play, tensors
from teacher.rules import step
from train.world_train import evaluate
from world.cells import EMPTY, FOOD, chain, length
from world.net import WorldNet
from world.start import start_field

MODEL = pathlib.Path(__file__).resolve().parents[1] / "models" / "world.npz"


@pytest.fixture(scope="module")
def net():
    return WorldNet.load(MODEL)


@pytest.fixture(scope="module")
def held_out():
    return tensors(play(np.random.default_rng(12345), 32, 32, 1500))


def test_whole_field_matches_the_rules(net, held_out):
    acc = evaluate(net, held_out)
    assert acc["field"] >= 0.995, acc


def test_events_match_the_rules(net, held_out):
    acc = evaluate(net, held_out)
    assert acc["events"] >= 0.999, acc


def test_food_is_not_born_on_snakes(net, held_out):
    acc = evaluate(net, held_out)
    assert acc["food_on_occupied"] < 0.01, acc


def lockstep(net, field, rng, steps, noise=0.05):
    """Ход за ходом: сеть и учитель из одного поля; после сравнения берётся поле учителя
    (новая еда у них по-разному случайна). Возвращает число ходов без расхождения."""
    for t in range(steps):
        a0 = greedy_move(field, 0, rng, noise)
        a1 = greedy_move(field, 1, rng, noise)
        o = step(field, a0, a1, rng)
        cells, ev, _, _ = net.predict(field, a0, a1)
        if tuple(bool(v) for v in ev[2:]) != o.crashed:
            return t
        if o.field is None:
            return steps
        if tuple(bool(v) for v in ev[:2]) != o.ate or not np.array_equal(cells, o.moved):
            return t
        field = o.field
    return steps


def test_long_snake_is_carried_correctly(net):
    """Сеть учили на коротких змейках на маленьких полях; змейку в 150 клеток она должна
    вести так же - правила местные, длина в них не входит."""
    rng = np.random.default_rng(7)
    done = 0
    for _ in range(5):
        field = np.zeros((32, 32), np.int8)
        while not grow(field, 0, 150, rng) or length(field, 0) < 100:
            field[:] = EMPTY
        assert grow(field, 1, 20, rng)
        empties = np.argwhere(field == EMPTY)
        field[tuple(empties[0])] = FOOD
        done += lockstep(net, field, rng, 50)
    assert done >= 5 * 50 * 0.97


def test_whole_rounds_from_the_start(net):
    rng = np.random.default_rng(3)
    total = sum(lockstep(net, start_field(), rng, 300) for _ in range(5))
    assert total >= 5 * 300 * 0.97


def test_net_game_keeps_snakes_whole(net):
    """Сеть ведёт мир сама (без учителя) 200 ходов: змейки не рвутся."""
    rng = np.random.default_rng(11)
    field = start_field()
    for _ in range(200):
        res = net.step(field, greedy_move(field, 0, rng, 0.0), greedy_move(field, 1, rng, 0.0), rng)
        if res.field is None:
            field = start_field()
            continue
        field = res.field
        assert chain(field, 0) is not None and chain(field, 1) is not None
        assert (field == FOOD).sum() == 1
