# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""UHX-16 cycle-approximate emulator.

64 KiB of byte-addressable memory, eight 16-bit registers, a downward
growing stack and three flags (Z, N, C). I/O happens through numbered ports
which the host wires up to Python callables.
"""

from __future__ import annotations

from typing import Callable

from .opcodes import Op, SPECS

MASK16 = 0xFFFF


class MachineFault(Exception):
    pass


class Machine:
    MEMORY_SIZE = 0x10000

    def __init__(self) -> None:
        self.memory = bytearray(self.MEMORY_SIZE)
        self.registers = [0] * 8
        self.pc = 0
        self.sp = 0xFFFE
        self.zero = False
        self.negative = False
        self.carry = False
        self.halted = False
        self.cycles = 0
        self.out_ports: dict[int, Callable[[int], None]] = {}
        self.in_ports: dict[int, Callable[[], int]] = {}
        self._dispatch = {op: getattr(self, f"_op_{op.name.lower()}") for op in Op}

    # ------------------------------------------------------------------ setup
    def load(self, image: bytes, origin: int = 0) -> None:
        if origin + len(image) > self.MEMORY_SIZE:
            raise MachineFault("image does not fit in memory")
        self.memory[origin:origin + len(image)] = image

    def attach_output(self, port: int, sink: Callable[[int], None]) -> None:
        self.out_ports[port] = sink

    def attach_input(self, port: int, source: Callable[[], int]) -> None:
        self.in_ports[port] = source

    # ---------------------------------------------------------------- helpers
    def _fetch8(self) -> int:
        value = self.memory[self.pc]
        self.pc = (self.pc + 1) & MASK16
        return value

    def _fetch16(self) -> int:
        lo = self._fetch8()
        return lo | (self._fetch8() << 8)

    def _set_flags(self, raw: int) -> int:
        result = raw & MASK16
        self.zero = result == 0
        self.negative = bool(result & 0x8000)
        self.carry = raw < 0 or raw > MASK16
        return result

    def _push(self, value: int) -> None:
        self.sp = (self.sp - 2) & MASK16
        self.memory[self.sp] = value & 0xFF
        self.memory[self.sp + 1] = (value >> 8) & 0xFF

    def _pop(self) -> int:
        value = self.memory[self.sp] | (self.memory[self.sp + 1] << 8)
        self.sp = (self.sp + 2) & MASK16
        return value

    # -------------------------------------------------------------- execution
    def step(self) -> None:
        opcode = self._fetch8()
        try:
            op = Op(opcode)
        except ValueError:
            raise MachineFault(f"illegal opcode 0x{opcode:02X} at 0x{(self.pc - 1) & MASK16:04X}")
        self._dispatch[op]()
        self.cycles += SPECS[op].size

    def run(self, max_cycles: int = 5_000_000) -> int:
        while not self.halted:
            if self.cycles > max_cycles:
                raise MachineFault("watchdog: program refuses to halt")
            self.step()
        return self.cycles

    # ----------------------------------------------------------- instructions
    def _op_nop(self): pass

    def _op_hlt(self):
        self.halted = True

    def _op_movi(self):
        rd = self._fetch8()
        self.registers[rd] = self._fetch16()

    def _op_mov(self):
        rd, rs = self._fetch8(), self._fetch8()
        self.registers[rd] = self.registers[rs]

    def _op_ldb(self):
        rd, rs = self._fetch8(), self._fetch8()
        self.registers[rd] = self.memory[self.registers[rs]]

    def _op_stb(self):
        rd, rs = self._fetch8(), self._fetch8()
        self.memory[self.registers[rd]] = self.registers[rs] & 0xFF

    def _alu(self, fn, store: bool = True):
        rd, rs = self._fetch8(), self._fetch8()
        result = self._set_flags(fn(self.registers[rd], self.registers[rs]))
        if store:
            self.registers[rd] = result

    def _alu_imm(self, fn, store: bool = True):
        rd = self._fetch8()
        result = self._set_flags(fn(self.registers[rd], self._fetch16()))
        if store:
            self.registers[rd] = result

    def _op_add(self): self._alu(lambda a, b: a + b)
    def _op_sub(self): self._alu(lambda a, b: a - b)
    def _op_and(self): self._alu(lambda a, b: a & b)
    def _op_or(self): self._alu(lambda a, b: a | b)
    def _op_xor(self): self._alu(lambda a, b: a ^ b)
    def _op_addi(self): self._alu_imm(lambda a, b: a + b)
    def _op_cmp(self): self._alu(lambda a, b: a - b, store=False)
    def _op_cmpi(self): self._alu_imm(lambda a, b: a - b, store=False)

    def _unary(self, fn):
        rd = self._fetch8()
        self.registers[rd] = self._set_flags(fn(self.registers[rd]))

    def _op_shl(self): self._unary(lambda a: a << 1)
    def _op_shr(self): self._unary(lambda a: a >> 1)
    def _op_inc(self): self._unary(lambda a: a + 1)
    def _op_dec(self): self._unary(lambda a: a - 1)

    def _jump_if(self, condition: bool):
        target = self._fetch16()
        if condition:
            self.pc = target

    def _op_jmp(self): self._jump_if(True)
    def _op_jz(self): self._jump_if(self.zero)
    def _op_jnz(self): self._jump_if(not self.zero)
    def _op_jc(self): self._jump_if(self.carry)
    def _op_jnc(self): self._jump_if(not self.carry)

    def _op_call(self):
        target = self._fetch16()
        self._push(self.pc)
        self.pc = target

    def _op_ret(self):
        self.pc = self._pop()

    def _op_push(self):
        self._push(self.registers[self._fetch8()])

    def _op_pop(self):
        self.registers[self._fetch8()] = self._pop()

    def _op_out(self):
        port, rs = self._fetch8(), self._fetch8()
        sink = self.out_ports.get(port)
        if sink is None:
            raise MachineFault(f"write to unmapped port 0x{port:02X}")
        sink(self.registers[rs])

    def _op_in(self):
        rd, port = self._fetch8(), self._fetch8()
        source = self.in_ports.get(port)
        if source is None:
            raise MachineFault(f"read from unmapped port 0x{port:02X}")
        self.registers[rd] = source() & MASK16
