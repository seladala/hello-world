"""Runtime anti-tamper and anti-cheat protection.

Detects debuggers, profilers, interactive inspection, monkey-patching of
critical code paths, output stream hijacking and clock manipulation
("speedhacks"). Scans run at boot and again right before rendering.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import time

from ..config import EnterpriseConfiguration
from ..events import EventBus
from ..output.terminal import TerminalRenderingEngine
from ..runtime.executor import Machine
from ..validation.normalization import LetterCaseNegotiator
from ..validation.policy import GlyphApprovalCommittee
from .errors import CheatDetected

log = logging.getLogger(__name__)

PROTECTED_CLASSES = (Machine, GlyphApprovalCommittee, LetterCaseNegotiator, TerminalRenderingEngine)


def _code_fingerprint(cls: type) -> str:
    digest = hashlib.sha256()
    for name in sorted(vars(cls)):
        member = vars(cls)[name]
        code = getattr(member, "__code__", None)
        if code is not None:
            digest.update(name.encode())
            digest.update(code.co_code)
            digest.update(repr(code.co_consts).encode())
    return digest.hexdigest()


def _snapshot() -> dict[str, str]:
    return {f"{cls.__module__}.{cls.__qualname__}": _code_fingerprint(cls) for cls in PROTECTED_CLASSES}


def _clock_ratio(duration: float = 0.005) -> float:
    """Ratio of wall-clock to monotonic time over a short busy wait."""
    wall_start, mono_start = time.time(), time.monotonic()
    while time.monotonic() - mono_start < duration:
        pass
    mono = time.monotonic() - mono_start
    return (time.time() - wall_start) / mono


class AntiCheatEngine:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus) -> None:
        self._tolerance = config.get_float("security", "clock_tolerance")
        self._bus = event_bus
        self._baseline: dict[str, str] = {}
        self._stdout = None
        self.scans = 0

    def on_start(self) -> None:
        self._baseline = _snapshot()
        self._stdout = sys.stdout
        self.scan()

    def scan(self) -> None:
        if sys.gettrace() is not None:
            raise CheatDetected("debugger or tracer attached")
        if sys.getprofile() is not None:
            raise CheatDetected("profiler attached")
        if sys.flags.inspect or os.environ.get("PYTHONINSPECT"):
            raise CheatDetected("interactive inspection mode enabled")
        if sys.stdout is not self._stdout:
            raise CheatDetected("standard output was hijacked after boot")
        tampered = [name for name, fp in _snapshot().items() if self._baseline.get(name) != fp]
        if tampered:
            raise CheatDetected(f"runtime code modification detected in {', '.join(tampered)}")
        ratio = _clock_ratio()
        if abs(ratio - 1.0) > self._tolerance:
            raise CheatDetected(f"clock manipulation detected (ratio {ratio:.2f})")
        self.scans += 1
        self._bus.publish("anticheat.scan.clean", self.scans)
        log.info("anti-cheat: scan #%d clean (%d protected classes)", self.scans, len(self._baseline))

    @staticmethod
    def verify_code_segment(machine: Machine, image: bytes) -> None:
        """Detect self-modifying firmware or memory editing during execution."""
        if bytes(machine.memory[:len(image)]) != bytes(image):
            raise CheatDetected("firmware code segment was modified during execution")
