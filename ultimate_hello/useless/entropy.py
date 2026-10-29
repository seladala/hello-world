"""An entropy pool that carefully gathers randomness and then never uses it."""

from __future__ import annotations

import hashlib
import logging

from ..config import EnterpriseConfiguration

log = logging.getLogger(__name__)


class EntropyPool:
    def __init__(self, config: EnterpriseConfiguration) -> None:
        self._rounds = config.get_int("warmup", "entropy_rounds")
        self._state = hashlib.sha512(b"ultimate hello world").digest()
        self.bits_collected = 0

    def stir(self, material: bytes) -> None:
        for _ in range(self._rounds):
            self._state = hashlib.sha512(self._state + material).digest()
        self.bits_collected += len(material) * 8

    def discard(self) -> int:
        """Throw the entropy away. Returns how many bits were heroically wasted."""
        wasted, self.bits_collected = self.bits_collected, 0
        self._state = bytes(len(self._state))
        log.info("entropy pool: %d bits discarded with full ceremony", wasted)
        return wasted
