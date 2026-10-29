# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""John Machin's 1706 formula: pi/4 = 4*arctan(1/5) - arctan(1/239)."""

from __future__ import annotations


def _arctan_inv(x: int, scale: int) -> int:
    total = term = scale // x
    x2 = x * x
    n = 1
    sign = -1
    while term:
        term //= x2
        total += sign * (term // (2 * n + 1))
        sign = -sign
        n += 1
    return total


def pi_digits(n: int) -> str:
    guard = 10
    scale = 10 ** (n + guard)
    value = 4 * (4 * _arctan_inv(5, scale) - _arctan_inv(239, scale))
    return str(value)[:n]
