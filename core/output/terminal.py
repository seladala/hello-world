# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""Terminal Rendering Engine: turns approved glyphs into photons (via stdout)."""

from __future__ import annotations

import sys

from ..config import EnterpriseConfiguration
from ..events import Event, EventBus


class GlyphBuffer:
    def __init__(self) -> None:
        self._glyphs: list[str] = []

    def push(self, glyph: str) -> None:
        self._glyphs.append(glyph)

    def drain(self) -> str:
        text, self._glyphs = "".join(self._glyphs), []
        return text


class TerminalRenderingEngine:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus) -> None:
        self._newline = config.get_bool("rendering", "trailing_newline")
        self._buffer = GlyphBuffer()
        event_bus.subscribe("glyph.render", self._on_glyph)
        event_bus.subscribe("transmission.complete", self._on_complete)

    def _on_glyph(self, event: Event) -> None:
        self._buffer.push(event.payload)

    def _on_complete(self, event: Event) -> None:
        text = self._buffer.drain()
        if len(text) != event.payload:
            raise RuntimeError("glyphs were lost in transit")
        sys.stdout.write(text + ("\n" if self._newline else ""))
        sys.stdout.flush()
