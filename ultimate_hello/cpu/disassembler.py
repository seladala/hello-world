"""Disassembler, so that the machine code can be reviewed by the Architecture Board."""

from __future__ import annotations

from .isa import Op, SPECS


def disassemble(image: bytes, start: int = 0, end: int | None = None) -> list[str]:
    end = len(image) if end is None else end
    lines: list[str] = []
    pc = start
    while pc < end:
        opcode = image[pc]
        try:
            spec = SPECS[Op(opcode)]
        except ValueError:
            spec = None
        if spec is None or pc + spec.size > end:
            lines.append(f"{pc:04X}:  {opcode:02X}            .byte 0x{opcode:02X}")
            pc += 1
            continue
        raw = image[pc:pc + spec.size]
        cursor = pc + 1
        parts = []
        for kind in spec.operands:
            if kind == "r":
                parts.append(f"R{image[cursor]}")
                cursor += 1
            elif kind == "p":
                parts.append(f"0x{image[cursor]:02X}")
                cursor += 1
            else:
                parts.append(f"0x{image[cursor] | (image[cursor + 1] << 8):04X}")
                cursor += 2
        lines.append(f"{pc:04X}:  {raw.hex(' ').upper():<14}{spec.mnemonic} {', '.join(parts)}".rstrip())
        pc += spec.size
    return lines
