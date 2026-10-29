"""Gibbons' unbounded spigot: streams digits of pi one at a time, forever."""

from __future__ import annotations

from itertools import islice
from typing import Iterator


def stream() -> Iterator[int]:
    q, r, t, k, n, l = 1, 0, 1, 1, 3, 3
    while True:
        if 4 * q + r - t < n * t:
            yield n
            q, r, n = 10 * q, 10 * (r - n * t), (10 * (3 * q + r)) // t - 10 * n
        else:
            q, r, t, k, n, l = (q * k, (2 * q + r) * l, t * l, k + 1,
                                (q * (7 * k + 2) + r * l) // (t * l), l + 2)


def pi_digits(n: int) -> str:
    return "".join(str(d) for d in islice(stream(), n))
