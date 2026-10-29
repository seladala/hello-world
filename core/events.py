"""Synchronous, in-process, single-threaded, enterprise-grade event bus."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable

log = logging.getLogger(__name__)

_sequence = count(1)


@dataclass(frozen=True)
class Event:
    topic: str
    payload: Any = None
    sequence: int = field(default_factory=lambda: next(_sequence))


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self.history: list[Event] = []

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> None:
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Any = None) -> Event:
        event = Event(topic, payload)
        self.history.append(event)
        log.debug("event #%05d %-28s %r", event.sequence, topic, payload)
        for handler in self._subscribers.get(topic, ()):
            handler(event)
        for handler in self._subscribers.get("*", ()):
            handler(event)
        return event
