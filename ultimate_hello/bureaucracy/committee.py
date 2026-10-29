"""The Glyph Approval Committee.

No character reaches the terminal without being reviewed by five independent
officers, majority-voted, stamped, and recorded on the GlyphChain.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import EnterpriseConfiguration
from ..events import EventBus
from .ledger import GlyphChain

log = logging.getLogger(__name__)


class GlyphRejected(Exception):
    pass


@dataclass(frozen=True)
class Verdict:
    officer: str
    approved: bool
    remark: str
    veto: bool = False


class Officer(ABC):
    title = "Officer"
    has_veto = False

    @abstractmethod
    def review(self, glyph: str, position: int, pi_digits: str) -> Verdict: ...

    def verdict(self, approved: bool, remark: str) -> Verdict:
        return Verdict(self.title, approved, remark, veto=self.has_veto and not approved)


class PrintabilityAuditor(Officer):
    title = "Printability Auditor"

    def review(self, glyph, position, pi_digits):
        return self.verdict(glyph.isprintable(), "visible to the naked eye")


class AsciiPurist(Officer):
    title = "ASCII Purist"

    def review(self, glyph, position, pi_digits):
        return self.verdict(ord(glyph) < 128, "no Unicode nonsense detected")


class PiNumerologist(Officer):
    title = "Pi Numerologist"

    def review(self, glyph, position, pi_digits):
        omen = int(pi_digits[position % len(pi_digits)])
        return self.verdict((ord(glyph) * omen) % 1 == 0, f"the digit {omen} looks favourable")


class VowelEqualityOfficer(Officer):
    title = "Vowel Equality Officer"

    def review(self, glyph, position, pi_digits):
        kind = "vowel" if glyph in "aeiou" else "consonant" if glyph.isalpha() else "neutral entity"
        return self.verdict(True, f"{kind} treated with equal respect")


class ChiefHelloOfficer(Officer):
    title = "Chief Hello Officer"
    has_veto = True
    _ALLOWED = frozenset("helowrd ")

    def review(self, glyph, position, pi_digits):
        return self.verdict(glyph.lower() in self._ALLOWED, "on-brand")


ALL_OFFICERS = (PrintabilityAuditor, AsciiPurist, PiNumerologist, VowelEqualityOfficer, ChiefHelloOfficer)


class GlyphApprovalCommittee:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus, pi_service, ledger: GlyphChain) -> None:
        self._officers = [cls() for cls in ALL_OFFICERS[: config.get_int("committee", "members")]]
        self._majority = config.get_float("committee", "required_majority")
        self._bus = event_bus
        self._pi = pi_service
        self._ledger = ledger

    def review(self, text: str) -> str:
        digits = self._pi.digits()
        approved = []
        for position, glyph in enumerate(text):
            verdicts = [officer.review(glyph, position, digits) for officer in self._officers]
            ayes = sum(v.approved for v in verdicts)
            vetoed = [v.officer for v in verdicts if v.veto]
            if vetoed or ayes / len(verdicts) < self._majority:
                raise GlyphRejected(f"glyph {glyph!r} at {position} rejected (ayes={ayes}, vetoes={vetoed})")
            self._ledger.append({"position": position, "glyph": glyph, "ayes": ayes,
                                 "stamps": [v.officer for v in verdicts]})
            self._bus.publish("glyph.approved", {"glyph": glyph, "ayes": f"{ayes}/{len(verdicts)}"})
            approved.append(glyph)
        self._ledger.verify()
        return "".join(approved)
