"""Byzantine-fault-tolerant consensus on the value of pi.

Three independent algorithms each propose digits. A digit string is accepted
only when a quorum of oracles agrees on it. If the universe ever disagrees
with itself about pi, we will be the first to know.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from . import chudnovsky, machin, spigot

log = logging.getLogger(__name__)


class PiConsensusFailure(Exception):
    pass


@dataclass(frozen=True)
class PiOracle:
    name: str
    compute: Callable[[int], str]
    max_digits: int


ORACLES = (
    PiOracle("Chudnovsky (1988)", chudnovsky.pi_digits, 1_000_000),
    PiOracle("Machin (1706)", machin.pi_digits, 50_000),
    PiOracle("Gibbons spigot (2006)", spigot.pi_digits, 2_000),
)


class PiConsensusProtocol:
    def __init__(self, oracles=ORACLES, quorum: int = 2) -> None:
        self.oracles = oracles
        self.quorum = quorum

    def agree(self, digits: int) -> str:
        proposals = []
        for oracle in self.oracles:
            proposal = oracle.compute(min(digits, oracle.max_digits))
            log.debug("oracle %-22s proposes %s... (%d digits)", oracle.name, proposal[:12], len(proposal))
            proposals.append(proposal)
        # Every full-length proposal is a candidate; oracles with a shorter
        # horizon endorse any candidate that extends what they can see.
        votes = Counter(
            candidate
            for candidate in {p for p in proposals if len(p) == digits}
            for proposal in proposals
            if candidate.startswith(proposal)
        )
        if not votes:
            raise PiConsensusFailure("no oracle could see far enough")
        winner, count = votes.most_common(1)[0]
        if count < self.quorum:
            raise PiConsensusFailure(f"no quorum on pi ({count}/{len(proposals)})")
        log.info("pi consensus reached: %d/%d oracles agree on %d digits", count, len(proposals), digits)
        return winner
