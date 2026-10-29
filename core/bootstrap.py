"""Kernel: resolves the dependency graph, boots every component, runs lifecycle hooks."""

from __future__ import annotations

import logging
from pathlib import Path

from .modules import load_manifest, resolve
from .container import Container
from .security import integrity

log = logging.getLogger(__name__)

DEFAULT_MANIFEST = Path(__file__).parent / "manifests" / "services.json"


class Kernel:
    def __init__(self, container: Container) -> None:
        self.container = container

    @classmethod
    def boot(cls, manifest: Path = DEFAULT_MANIFEST) -> "Kernel":
        integrity.verify()
        order = resolve(load_manifest(manifest))
        log.info("boot order: %s", " -> ".join(c.name for c in order))
        container = Container()
        for component in order:
            instance = container.instantiate(component)
            if hasattr(instance, "on_start"):
                instance.on_start()
        container.get("event_bus").publish("kernel.booted", len(order))
        return cls(container)

    def produce_greeting(self) -> str:
        return self.container.get("greeting_service").produce()

    def render(self, message: str) -> None:
        self.container.get("greeting_service").deliver(message)
