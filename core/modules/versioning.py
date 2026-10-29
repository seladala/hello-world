# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""A semantic versioning implementation, because "1.2.3" is too hard to compare by eye."""

from __future__ import annotations

import operator
import re
from functools import total_ordering

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_CONSTRAINT_RE = re.compile(r"^(>=|<=|==|!=|>|<|\^|~)?\s*(\d+(?:\.\d+){0,2})$")
_OPERATORS = {
    ">=": operator.ge, "<=": operator.le, "==": operator.eq,
    "!=": operator.ne, ">": operator.gt, "<": operator.lt,
}


@total_ordering
class Version:
    def __init__(self, text: str) -> None:
        match = _VERSION_RE.match(text.strip())
        if not match:
            raise ValueError(f"not a semantic version: {text!r}")
        self.parts = tuple(int(p) for p in match.groups())

    @classmethod
    def loose(cls, text: str) -> "Version":
        parts = (text.split(".") + ["0", "0"])[:3]
        return cls(".".join(parts))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self.parts == other.parts

    def __lt__(self, other: "Version") -> bool:
        return self.parts < other.parts

    def __hash__(self) -> int:
        return hash(self.parts)

    def __str__(self) -> str:
        return ".".join(map(str, self.parts))


def satisfies(version: Version, spec: str) -> bool:
    """Check a version against a comma-separated constraint list, e.g. '>=1.2,<2'."""
    for clause in filter(None, (c.strip() for c in spec.split(","))):
        match = _CONSTRAINT_RE.match(clause)
        if not match:
            raise ValueError(f"bad constraint: {clause!r}")
        op, raw = match.groups()
        target = Version.loose(raw)
        if op == "^":
            ok = version >= target and version.parts[0] == target.parts[0]
        elif op == "~":
            ok = version >= target and version.parts[:2] == target.parts[:2]
        else:
            ok = _OPERATORS[op or "=="](version, target)
        if not ok:
            return False
    return True
