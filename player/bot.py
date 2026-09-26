"""Бот, которому подражает сеть-соперник при обучении. В игре не участвует.

Ход выбирается по порядку важности: не подставляться под лобовое столкновение, не лезть в
область меньше своей длины (тупик), идти кратчайшим путём к еде, при прочих равных - туда,
где больше места.
"""
from collections import deque

import numpy as np

from world.cells import DELTA, EMPTY, FOOD, OPPOSITE, head, heading, length

FLOOD_LIMIT = 200


def _free(field, cell):
    H, W = field.shape
    return 0 <= cell[0] < H and 0 <= cell[1] < W and field[cell] in (EMPTY, FOOD)


def flood(field, start, limit=None):
    """Сколько свободных клеток достижимо из start (включая её); с limit - счёт до limit."""
    if not _free(field, start):
        return 0
    seen = {start}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in DELTA:
            n = (r + dr, c + dc)
            if n not in seen and _free(field, n):
                seen.add(n)
                if limit and len(seen) >= limit:
                    return len(seen)
                queue.append(n)
    return len(seen)


def food_distance(field):
    """Расстояние в шагах от каждой свободной клетки до ближайшей еды (обход препятствий)."""
    H, W = field.shape
    dist = np.full((H, W), 10 ** 6, np.int32)
    queue = deque()
    for f in np.argwhere(field == FOOD):
        f = (int(f[0]), int(f[1]))
        dist[f] = 0
        queue.append(f)
    while queue:
        r, c = queue.popleft()
        for dr, dc in DELTA:
            n = (r + dr, c + dc)
            if _free(field, n) and dist[n] > dist[r, c] + 1:
                dist[n] = dist[r, c] + 1
                queue.append(n)
    return dist


def bot_move(field, s):
    h = head(field, s)
    d0 = heading(field, s)
    size = length(field, s)
    other = head(field, 1 - s)
    danger = set()
    if other is not None:
        danger = {(other[0] + dr, other[1] + dc) for dr, dc in DELTA}
    dist = None
    best, best_key = d0, None
    for d in range(4):
        if d == OPPOSITE[d0]:
            continue
        t = (h[0] + DELTA[d][0], h[1] + DELTA[d][1])
        if not _free(field, t):
            continue
        if dist is None:
            dist = food_distance(field)
        area = flood(field, t, limit=max(FLOOD_LIMIT, 2 * size))
        key = (t not in danger, area >= size, -int(dist[t]), area)
        if best_key is None or key > best_key:
            best, best_key = d, key
    return best
