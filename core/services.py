# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""Core services. Each one does a small job in the largest possible number of steps."""

from __future__ import annotations

import logging
from pathlib import Path

from .validation.policy import GlyphApprovalCommittee
from .validation.normalization import LetterCaseNegotiator
from .config import EnterpriseConfiguration
from .runtime import AssembledProgram, Machine, MachineFault, assemble, disassemble
from .events import EventBus
from .numerics import PiConsensusProtocol
from .output.terminal import TerminalRenderingEngine
from .security.anticheat import AntiCheatEngine
from .security.drm import LicenseManager
from .diagnostics.arithmetic import peano_length, to_int

log = logging.getLogger(__name__)

PROGRAMS_DIR = Path(__file__).parent / "runtime" / "firmware"

PORT_TTY = 0x01
PORT_STATUS = 0x02
PORT_FIB = 0x10
PORT_RAM = 0x11
STATUS_GOOD = 0x600D


class PiService:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus) -> None:
        self._protocol = PiConsensusProtocol(quorum=config.get_int("pi", "quorum"))
        self._count = config.get_int("pi", "digits")
        self._bus = event_bus
        self._digits: str | None = None

    def digits(self) -> str:
        if self._digits is None:
            self._digits = self._protocol.agree(self._count)
            self._bus.publish("pi.agreed", self._digits[:10] + "...")
        return self._digits


class FirmwareLoader:
    def __init__(self, config: EnterpriseConfiguration) -> None:
        self._cache: dict[str, AssembledProgram] = {}

    def load(self, name: str) -> AssembledProgram:
        if name not in self._cache:
            program = assemble((PROGRAMS_DIR / name).read_text(encoding="utf-8"))
            listing = disassemble(program.image)
            log.info("firmware %s: %d bytes, %d disassembled lines, %d symbols",
                     name, len(program.image), len(listing), len(program.symbols))
            for line in listing:
                log.debug("  %s", line)
            self._cache[name] = program
        return self._cache[name]


class CpuService:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus,
                 firmware_loader: FirmwareLoader, pi_service: PiService,
                 anticheat: AntiCheatEngine) -> None:
        self._config = config
        self._anticheat = anticheat
        self._bus = event_bus
        self._loader = firmware_loader
        self._pi = pi_service

    def on_start(self) -> None:
        self.run_self_test()

    def run_self_test(self) -> None:
        machine = Machine()
        machine.load(self._loader.load(self._config.get("cpu", "self_test")).image)
        results: dict[str, int] = {}
        machine.attach_output(PORT_FIB, lambda v: results.__setitem__("fib", v))
        machine.attach_output(PORT_RAM, lambda v: results.__setitem__("ram_errors", v))
        cycles = machine.run(self._config.get_int("cpu", "watchdog_cycles"))
        if results != {"fib": 6765, "ram_errors": 0}:
            raise MachineFault(f"POST failed: {results}")
        self._bus.publish("cpu.post.passed", {"cycles": cycles, **results})

    def execute_firmware(self) -> str:
        firmware = self._loader.load(self._config.get("cpu", "firmware"))
        machine = Machine()
        machine.load(firmware.image)
        machine.load(bytes(int(d) for d in self._pi.digits()), self._config.get_int("cpu", "pi_digits_address"))
        output: list[str] = []
        status: list[int] = []
        machine.attach_output(PORT_TTY, lambda v: output.append(chr(v & 0xFF)))
        machine.attach_output(PORT_STATUS, status.append)
        cycles = machine.run(self._config.get_int("cpu", "watchdog_cycles"))
        self._anticheat.verify_code_segment(machine, firmware.image)
        if status != [STATUS_GOOD]:
            raise MachineFault(f"firmware reported bad status: {status}")
        emulated_seconds = cycles / self._config.get_int("cpu", "clock_hz")
        self._bus.publish("cpu.firmware.halted", {"cycles": cycles, "emulated_seconds": emulated_seconds})
        return "".join(output)


class GreetingService:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus, cpu_service: CpuService,
                 committee: GlyphApprovalCommittee, case_negotiator: LetterCaseNegotiator,
                 renderer: TerminalRenderingEngine, drm: LicenseManager,
                 anticheat: AntiCheatEngine) -> None:
        self._config = config
        self._drm = drm
        self._anticheat = anticheat
        self._bus = event_bus
        self._cpu = cpu_service
        self._committee = committee
        self._negotiator = case_negotiator
        self._renderer = renderer

    def produce(self) -> str:
        self._drm.require("greeting.produce")
        raw = self._cpu.execute_firmware()
        for index, glyph in enumerate(raw):
            self._bus.publish("glyph.received", (index, glyph))
        approved = self._committee.review(raw)
        final = self._negotiator.negotiate(approved)
        if to_int(peano_length(final)) != self._config.get_int("greeting", "expected_length"):
            raise ValueError("greeting failed Peano length verification")
        return final

    def deliver(self, message: str) -> None:
        self._drm.require("greeting.render")
        self._anticheat.scan()
        for glyph in message:
            self._bus.publish("glyph.render", glyph)
        self._bus.publish("transmission.complete", len(message))
