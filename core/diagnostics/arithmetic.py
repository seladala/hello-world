"""Peano arithmetic, for counting characters the way Giuseppe intended."""

from __future__ import annotations

from dataclasses import dataclass


class Zero:
    _instance: "Zero | None" = None

    def __new__(cls) -> "Zero":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "Z"


@dataclass(frozen=True)
class Succ:
    predecessor: "Zero | Succ"

    def __repr__(self) -> str:
        return f"S({self.predecessor!r})"


Natural = Zero | Succ
ZERO = Zero()


def add(a: Natural, b: Natural) -> Natural:
    while isinstance(b, Succ):
        a, b = Succ(a), b.predecessor
    return a


def peano_length(sequence) -> Natural:
    total: Natural = ZERO
    for _ in sequence:
        total = add(total, Succ(ZERO))
    return total


def to_int(n: Natural) -> int:
    count = 0
    while isinstance(n, Succ):
        n, count = n.predecessor, count + 1
    return count
