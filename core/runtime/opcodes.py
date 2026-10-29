# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""UHX-16 Instruction Set Architecture.

The Unified Hardware eXecution unit is a 16-bit, 8-register, little-endian
CPU designed by a committee whose only requirement was "it must be able to
say hello world, eventually".

Operand kinds:
    "r" - register index, 1 byte (R0..R7)
    "i" - 16-bit immediate / address, 2 bytes little-endian
    "p" - 8-bit I/O port number, 1 byte
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Op(IntEnum):
    NOP = 0x00
    HLT = 0x01

    MOVI = 0x10
    MOV = 0x11
    LDB = 0x12
    STB = 0x13

    ADD = 0x20
    SUB = 0x21
    AND = 0x22
    OR = 0x23
    XOR = 0x24
    ADDI = 0x25
    CMP = 0x26
    CMPI = 0x27
    SHL = 0x28
    SHR = 0x29
    INC = 0x2A
    DEC = 0x2B

    JMP = 0x30
    JZ = 0x31
    JNZ = 0x32
    JC = 0x33
    JNC = 0x34

    CALL = 0x38
    RET = 0x39
    PUSH = 0x3A
    POP = 0x3B

    OUT = 0x40
    IN = 0x41


@dataclass(frozen=True)
class InstructionSpec:
    op: Op
    operands: str
    description: str

    @property
    def mnemonic(self) -> str:
        return self.op.name

    @property
    def size(self) -> int:
        return 1 + sum(OPERAND_SIZES[kind] for kind in self.operands)


OPERAND_SIZES = {"r": 1, "i": 2, "p": 1}

REGISTER_COUNT = 8

SPECS: dict[Op, InstructionSpec] = {
    spec.op: spec
    for spec in (
        InstructionSpec(Op.NOP, "", "do nothing, but professionally"),
        InstructionSpec(Op.HLT, "", "stop the world"),
        InstructionSpec(Op.MOVI, "ri", "rd <- imm16"),
        InstructionSpec(Op.MOV, "rr", "rd <- rs"),
        InstructionSpec(Op.LDB, "rr", "rd <- mem8[rs]"),
        InstructionSpec(Op.STB, "rr", "mem8[rd] <- rs & 0xFF"),
        InstructionSpec(Op.ADD, "rr", "rd <- rd + rs"),
        InstructionSpec(Op.SUB, "rr", "rd <- rd - rs"),
        InstructionSpec(Op.AND, "rr", "rd <- rd & rs"),
        InstructionSpec(Op.OR, "rr", "rd <- rd | rs"),
        InstructionSpec(Op.XOR, "rr", "rd <- rd ^ rs"),
        InstructionSpec(Op.ADDI, "ri", "rd <- rd + imm16"),
        InstructionSpec(Op.CMP, "rr", "flags <- rd - rs"),
        InstructionSpec(Op.CMPI, "ri", "flags <- rd - imm16"),
        InstructionSpec(Op.SHL, "r", "rd <- rd << 1"),
        InstructionSpec(Op.SHR, "r", "rd <- rd >> 1"),
        InstructionSpec(Op.INC, "r", "rd <- rd + 1"),
        InstructionSpec(Op.DEC, "r", "rd <- rd - 1"),
        InstructionSpec(Op.JMP, "i", "pc <- addr"),
        InstructionSpec(Op.JZ, "i", "if Z: pc <- addr"),
        InstructionSpec(Op.JNZ, "i", "if !Z: pc <- addr"),
        InstructionSpec(Op.JC, "i", "if C: pc <- addr"),
        InstructionSpec(Op.JNC, "i", "if !C: pc <- addr"),
        InstructionSpec(Op.CALL, "i", "push pc; pc <- addr"),
        InstructionSpec(Op.RET, "", "pc <- pop"),
        InstructionSpec(Op.PUSH, "r", "push rs"),
        InstructionSpec(Op.POP, "r", "rd <- pop"),
        InstructionSpec(Op.OUT, "pr", "port <- rs"),
        InstructionSpec(Op.IN, "rp", "rd <- port"),
    )
}

MNEMONICS: dict[str, InstructionSpec] = {spec.mnemonic: spec for spec in SPECS.values()}
