"""Warm-up routines. None of them influence the output. All of them are mandatory."""

from __future__ import annotations

import logging
import random
from fractions import Fraction

from ..config import EnterpriseConfiguration
from .entropy import EntropyPool

log = logging.getLogger(__name__)

KNOWN_PRIME_COUNTS = {1000: 168, 10000: 1229, 20000: 2262, 100000: 9592}


class WarmupFailure(Exception):
    pass


def verify_collatz(limit: int) -> int:
    """Check the Collatz conjecture up to `limit`. Returns the longest trajectory found."""
    known = {1: 0}
    longest = 0
    for start in range(1, limit + 1):
        path, n = [], start
        while n not in known:
            path.append(n)
            n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps = known[n]
        for value in reversed(path):
            steps += 1
            known[value] = steps
        longest = max(longest, known[start])
    return longest


def count_primes(limit: int) -> int:
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytes(len(range(i * i, limit + 1, i)))
    return sum(sieve)


def identity_determinant(size: int) -> Fraction:
    """Gaussian elimination on the identity matrix, in exact rational arithmetic."""
    m = [[Fraction(int(r == c)) for c in range(size)] for r in range(size)]
    det = Fraction(1)
    for col in range(size):
        pivot = next(r for r in range(col, size) if m[r][col] != 0)
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
            det = -det
        det *= m[col][col]
        for r in range(col + 1, size):
            factor = m[r][col] / m[col][col]
            m[r] = [a - factor * b for a, b in zip(m[r], m[col])]
    return det


def bogosort(items: list[int], rng: random.Random) -> tuple[list[int], int]:
    items = list(items)
    attempts = 0
    while any(a > b for a, b in zip(items, items[1:])):
        rng.shuffle(items)
        attempts += 1
    return items, attempts


class WarmupOrchestrator:
    def __init__(self, config: EnterpriseConfiguration, entropy_pool: EntropyPool) -> None:
        self._config = config
        self._entropy = entropy_pool

    def on_start(self) -> None:
        cfg = self._config
        longest = verify_collatz(cfg.get_int("warmup", "collatz_limit"))
        log.info("warmup: Collatz conjecture holds (longest trajectory: %d steps)", longest)

        limit = cfg.get_int("warmup", "sieve_limit")
        primes = count_primes(limit)
        if limit in KNOWN_PRIME_COUNTS and primes != KNOWN_PRIME_COUNTS[limit]:
            raise WarmupFailure(f"number theory is broken: pi({limit}) = {primes}")
        log.info("warmup: %d primes below %d, as expected", primes, limit)

        det = identity_determinant(cfg.get_int("warmup", "matrix_size"))
        if det != 1:
            raise WarmupFailure(f"det(I) = {det}")
        log.info("warmup: det(I) = 1, linear algebra operational")

        rng = random.Random(0xC0FFEE)
        size = cfg.get_int("warmup", "bogosort_size")
        result, attempts = bogosort(rng.sample(range(100), size), rng)
        log.info("warmup: bogosort sorted %s in %d attempts", result, attempts)

        self._entropy.stir(repr((longest, primes, det, result, attempts)).encode())
        self._entropy.discard()
