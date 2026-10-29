"""Inversion-of-Control container.

Components are instantiated in dependency order; each provider receives its
dependencies as keyword arguments named after the components it requires.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from .deps import Component

log = logging.getLogger(__name__)


class ContainerError(Exception):
    pass


def import_provider(path: str) -> Any:
    module_name, _, attr = path.partition(":")
    return getattr(importlib.import_module(module_name), attr)


class Container:
    def __init__(self) -> None:
        self._instances: dict[str, Any] = {}

    def register_instance(self, name: str, instance: Any) -> None:
        self._instances[name] = instance

    def instantiate(self, component: Component) -> Any:
        if component.name in self._instances:
            raise ContainerError(f"component already running: {component.name}")
        provider = import_provider(component.provider)
        kwargs = {dep: self.get(dep) for dep in component.requires}
        instance = provider(**kwargs)
        self._instances[component.name] = instance
        log.info("started %-18s v%-6s <- %s", component.name, component.version, component.provider)
        return instance

    def get(self, name: str) -> Any:
        try:
            return self._instances[name]
        except KeyError:
            raise ContainerError(f"component not running: {name}") from None

    def __contains__(self, name: str) -> bool:
        return name in self._instances
