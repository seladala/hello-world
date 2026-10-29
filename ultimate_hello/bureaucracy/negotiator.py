"""Letter case is decided through structured multi-round negotiation."""

from __future__ import annotations

import logging

from ..config import EnterpriseConfiguration

log = logging.getLogger(__name__)

_PROPOSALS = {
    "UPPER": str.upper,
    "Title": str.title,
    "Sentence": str.capitalize,
    "lower": str.lower,
}


class NegotiationDeadlock(Exception):
    pass


class LetterCaseNegotiator:
    def __init__(self, config: EnterpriseConfiguration) -> None:
        self._mandate = config.get("greeting", "case")
        self._separator_policy = config.get("greeting", "separator_policy")

    def negotiate(self, text: str) -> str:
        for round_no, (name, transform) in enumerate(_PROPOSALS.items(), start=1):
            proposal = transform(text)
            accepted = name.lower() == self._mandate.lower()
            log.info("case negotiation round %d: %-8s -> %r %s", round_no, name, proposal,
                     "ACCEPTED" if accepted else "rejected, escalating")
            if accepted:
                return self._enforce_separators(proposal)
        raise NegotiationDeadlock(f"no proposal satisfies mandate {self._mandate!r}")

    def _enforce_separators(self, text: str) -> str:
        if self._separator_policy == "single-space":
            return " ".join(text.split())
        return text
