"""Deterministic layer and service-dependency graph checks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .models import Finding, ServiceEdge


def find_cycles(edges: Iterable[ServiceEdge]) -> tuple[tuple[str, ...], ...]:
    graph: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for edge in edges:
        graph[edge.source].append(edge.target)
        nodes.update((edge.source, edge.target))
    for targets in graph.values():
        targets.sort()

    cycles: set[tuple[str, ...]] = set()
    active: list[str] = []
    state: dict[str, int] = {}

    def canonical(cycle: list[str]) -> tuple[str, ...]:
        ring = cycle[:-1]
        rotations = [tuple(ring[index:] + ring[:index]) for index in range(len(ring))]
        smallest = min(rotations)
        return smallest + (smallest[0],)

    def visit(node: str) -> None:
        state[node] = 1
        active.append(node)
        for target in graph[node]:
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1:
                index = active.index(target)
                cycles.add(canonical(active[index:] + [target]))
        active.pop()
        state[node] = 2

    for node in sorted(nodes):
        if state.get(node, 0) == 0:
            visit(node)
    return tuple(sorted(cycles))


def layer_findings(imports: Iterable[dict[str, Any]]) -> list[Finding]:
    result: list[Finding] = []
    for item in imports:
        file_name = str(item["file"])
        module = str(item["module"])
        if file_name.startswith("src/domain/") and module.startswith("src.infrastructure"):
            result.append(
                Finding(
                    rule_id="ARCH-LAYER-001",
                    code="LAYER_DEPENDENCY_VIOLATION",
                    resource=file_name,
                    disposition="BLOCK",
                    message="Domain code must not depend on infrastructure code.",
                    evidence=(f"{file_name}:{item['line']}", module),
                )
            )
    return result


def service_graph_findings(
    edges: Iterable[ServiceEdge],
    allowed_edges: set[tuple[str, str, str]],
) -> list[Finding]:
    values = tuple(edges)
    result: list[Finding] = []
    for edge in values:
        if (edge.source, edge.target, edge.mode) not in allowed_edges:
            result.append(
                Finding(
                    rule_id="EA-005",
                    code="SERVICE_DEPENDENCY_NOT_ALLOWED",
                    resource=f"{edge.source}->{edge.target}",
                    disposition="BLOCK",
                    message="The service edge is not present in the approved reference architecture.",
                    evidence=(edge.mode,),
                )
            )
    for cycle in find_cycles(values):
        result.append(
            Finding(
                rule_id="EA-006",
                code="SERVICE_DEPENDENCY_CYCLE",
                resource=" -> ".join(cycle),
                disposition="BLOCK",
                message="The candidate service graph contains a dependency cycle.",
                evidence=("service-dependencies.json",),
            )
        )
    return result
