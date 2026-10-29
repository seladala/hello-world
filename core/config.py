"""Strongly-typed-ish configuration facade over a perfectly ordinary .ini file."""

from __future__ import annotations

import configparser
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("settings.ini")


class EnterpriseConfiguration:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._parser = configparser.ConfigParser(inline_comment_prefixes=(";",))
        if not self._parser.read(path, encoding="utf-8"):
            raise FileNotFoundError(f"enterprise configuration missing: {path}")

    def get(self, section: str, key: str) -> str:
        return self._parser.get(section, key)

    def get_int(self, section: str, key: str) -> int:
        return int(self._parser.get(section, key), 0)

    def get_float(self, section: str, key: str) -> float:
        return self._parser.getfloat(section, key)

    def get_bool(self, section: str, key: str) -> bool:
        return self._parser.getboolean(section, key)
