"""GlyphChain: a proof-of-work blockchain that records every approved character.

Decentralised across exactly one process.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..config import EnterpriseConfiguration
from ..events import EventBus

GENESIS_HASH = "0" * 64


class LedgerCorruption(Exception):
    pass


@dataclass(frozen=True)
class Block:
    index: int
    data: dict
    previous_hash: str
    nonce: int
    hash: str


def _digest(index: int, data: dict, previous_hash: str, nonce: int) -> str:
    body = json.dumps([index, data, previous_hash, nonce], sort_keys=True).encode()
    return hashlib.sha256(body).hexdigest()


class GlyphChain:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus) -> None:
        self._difficulty = config.get_int("ledger", "difficulty")
        self._bus = event_bus
        self.blocks: list[Block] = []

    def append(self, data: dict) -> Block:
        index = len(self.blocks)
        previous = self.blocks[-1].hash if self.blocks else GENESIS_HASH
        prefix = "0" * self._difficulty
        nonce = 0
        while not (digest := _digest(index, data, previous, nonce)).startswith(prefix):
            nonce += 1
        block = Block(index, data, previous, nonce, digest)
        self.blocks.append(block)
        self._bus.publish("ledger.block.mined", {"index": index, "nonce": nonce, "hash": digest[:12]})
        return block

    def verify(self) -> None:
        previous = GENESIS_HASH
        for block in self.blocks:
            if block.previous_hash != previous:
                raise LedgerCorruption(f"block {block.index} is not linked to its parent")
            if _digest(block.index, block.data, block.previous_hash, block.nonce) != block.hash:
                raise LedgerCorruption(f"block {block.index} has been tampered with")
            previous = block.hash
