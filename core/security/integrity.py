"""File integrity verification.

Every source file, firmware image, configuration file and main.py is pinned
by SHA-256 in checksums.sha256. Modified, missing or unexpected files abort
startup before a single module is resolved.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .errors import IntegrityViolation

log = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_DIR.parent
CHECKSUMS = Path(__file__).with_name("checksums.sha256")
ENTRY_POINT = PROJECT_ROOT / "main.py"


def protected_files() -> list[Path]:
    files = [ENTRY_POINT]
    for path in sorted(PACKAGE_DIR.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path != CHECKSUMS:
            files.append(path)
    return files


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_manifest() -> dict[str, str]:
    return {path.relative_to(PROJECT_ROOT).as_posix(): sha256_of(path) for path in protected_files()}


def load_manifest(path: Path = CHECKSUMS) -> dict[str, str]:
    if not path.exists():
        raise IntegrityViolation(f"integrity manifest missing: {path.name}")
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            entries[name.strip()] = digest
    return entries


def verify() -> int:
    expected = load_manifest()
    actual = compute_manifest()
    missing = sorted(expected.keys() - actual.keys())
    unexpected = sorted(actual.keys() - expected.keys())
    modified = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    if missing or unexpected or modified:
        details = "; ".join(
            f"{label}: {', '.join(names)}"
            for label, names in (("modified", modified), ("missing", missing), ("unexpected", unexpected))
            if names
        )
        raise IntegrityViolation(f"file integrity check failed ({details})")
    log.info("integrity: %d files verified against SHA-256 manifest", len(actual))
    return len(actual)
