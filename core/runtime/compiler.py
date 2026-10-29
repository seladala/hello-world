"""Two-pass assembler for UHX-16 assembly.

Syntax:
    label:                  define a label
    MNEMONIC op, op         instruction (registers R0..R7, [Rn] allowed for LDB/STB)
    .org  ADDR              move the location counter forward
    .equ  NAME, VALUE       define a constant
    .byte v, v, ...         emit bytes
    .word v, v, ...         emit 16-bit little-endian words
    ; comment

Values may be decimal, 0x-hex, 0b-binary, or a symbol name.
String literals are deliberately unsupported: typing "hello world" would be cheating.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .opcodes import MNEMONICS, OPERAND_SIZES, REGISTER_COUNT


class AssemblyError(Exception):
    pass


@dataclass
class AssembledProgram:
    image: bytearray
    symbols: dict[str, int] = field(default_factory=dict)
    listing: list[tuple[int, str]] = field(default_factory=list)


_LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
_REGISTER_RE = re.compile(r"^\[?R([0-9])\]?$", re.IGNORECASE)


def _split_operands(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_register(token: str, line_no: int) -> int:
    match = _REGISTER_RE.match(token)
    if not match or int(match.group(1)) >= REGISTER_COUNT:
        raise AssemblyError(f"line {line_no}: expected register, got {token!r}")
    return int(match.group(1))


def _parse_value(token: str, symbols: dict[str, int], line_no: int, strict: bool) -> int:
    token = token.strip()
    try:
        return int(token, 0)
    except ValueError:
        pass
    if token in symbols:
        return symbols[token]
    if strict:
        raise AssemblyError(f"line {line_no}: unknown symbol {token!r}")
    return 0


def _clean_lines(source: str):
    for line_no, raw in enumerate(source.splitlines(), start=1):
        line = raw.split(";", 1)[0].strip()
        if line:
            yield line_no, line


def _size_of(line: str, symbols: dict[str, int], line_no: int, location: int) -> tuple[int, int]:
    """Return (new_location, emitted_size) for a label-free line."""
    head, _, rest = line.partition(" ")
    head = head.upper()
    operands = _split_operands(rest)
    if head == ".ORG":
        target = _parse_value(operands[0], symbols, line_no, strict=True)
        if target < location:
            raise AssemblyError(f"line {line_no}: .org moves backwards")
        return target, 0
    if head == ".EQU":
        return location, 0
    if head == ".BYTE":
        return location + len(operands), len(operands)
    if head == ".WORD":
        return location + 2 * len(operands), 2 * len(operands)
    spec = MNEMONICS.get(head)
    if spec is None:
        raise AssemblyError(f"line {line_no}: unknown mnemonic {head!r}")
    return location + spec.size, spec.size


def assemble(source: str) -> AssembledProgram:
    lines = list(_clean_lines(source))
    symbols: dict[str, int] = {}

    # Pass 1: assign addresses to labels and constants.
    location = 0
    for line_no, line in lines:
        while (match := _LABEL_RE.match(line)):
            name = match.group(1)
            if name in symbols:
                raise AssemblyError(f"line {line_no}: duplicate symbol {name!r}")
            symbols[name] = location
            line = line[match.end():].strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        if head.upper() == ".EQU":
            name, value = _split_operands(rest)
            symbols[name] = _parse_value(value, symbols, line_no, strict=True)
            continue
        location, _ = _size_of(line, symbols, line_no, location)

    # Pass 2: emit bytes.
    image = bytearray()
    listing: list[tuple[int, str]] = []
    for line_no, line in lines:
        while (match := _LABEL_RE.match(line)):
            line = line[match.end():].strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        head = head.upper()
        operands = _split_operands(rest)
        if head == ".EQU":
            continue
        if head == ".ORG":
            target = _parse_value(operands[0], symbols, line_no, strict=True)
            image.extend(b"\x00" * (target - len(image)))
            continue
        listing.append((len(image), line))
        if head == ".BYTE":
            for token in operands:
                value = _parse_value(token, symbols, line_no, strict=True)
                if not 0 <= value <= 0xFF:
                    raise AssemblyError(f"line {line_no}: byte out of range: {value}")
                image.append(value)
            continue
        if head == ".WORD":
            for token in operands:
                value = _parse_value(token, symbols, line_no, strict=True) & 0xFFFF
                image.extend(value.to_bytes(2, "little"))
            continue
        spec = MNEMONICS[head]
        if len(operands) != len(spec.operands):
            raise AssemblyError(
                f"line {line_no}: {head} expects {len(spec.operands)} operands, got {len(operands)}"
            )
        image.append(spec.op)
        for kind, token in zip(spec.operands, operands):
            if kind == "r":
                image.append(_parse_register(token, line_no))
            else:
                value = _parse_value(token, symbols, line_no, strict=True)
                size = OPERAND_SIZES[kind]
                image.extend((value & ((1 << (8 * size)) - 1)).to_bytes(size, "little"))
    return AssembledProgram(image=image, symbols=symbols, listing=listing)
