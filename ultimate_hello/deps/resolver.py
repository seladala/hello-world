"""Dependency resolution for internal components.

Reads a JSON manifest, validates every version constraint, detects cycles
and produces a deterministic topological boot order (Kahn's algorithm).
"""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path

from .semver import Version, satisfies


class DependencyError(Exception):
    pass


@dataclass(frozen=True)
class Component:
    name: str
    version: Version
    provider: str
    requires: dict[str, str]
    description: str = ""


def load_manifest(path: Path) -> dict[str, Component]:
    data = json.loads(path.read_text(encoding="utf-8"))
    components = {}
    for entry in data["components"]:
        component = Component(
            name=entry["name"],
            version=Version(entry["version"]),
            provider=entry["provider"],
            requires=dict(entry.get("requires", {})),
            description=entry.get("description", ""),
        )
        if component.name in components:
            raise DependencyError(f"component declared twice: {component.name}")
        components[component.name] = component
    return components


def resolve(components: dict[str, Component]) -> list[Component]:
    indegree = {name: 0 for name in components}
    dependents: dict[str, list[str]] = {name: [] for name in components}
    for component in components.values():
        for dep, spec in component.requires.items():
            if dep not in components:
                raise DependencyError(f"{component.name} requires missing component {dep!r}")
            if not satisfies(components[dep].version, spec):
                raise DependencyError(
                    f"{component.name} requires {dep} {spec}, found {components[dep].version}"
                )
            indegree[component.name] += 1
            dependents[dep].append(component.name)

    ready = [name for name, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[Component] = []
    while ready:
        name = heapq.heappop(ready)
        order.append(components[name])
        for dependent in dependents[name]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    if len(order) != len(components):
        stuck = sorted(name for name, degree in indegree.items() if degree)
        raise DependencyError(f"dependency cycle among: {', '.join(stuck)}")
    return order
