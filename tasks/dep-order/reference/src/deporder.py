"""Deterministic build order for a dependency graph. See task.md."""

from __future__ import annotations

import heapq


class CycleError(ValueError):
    """Raised when the graph contains a cycle.

    `.cycle` names the members of the reported cycle, in depends-on order,
    without repeating the first member at the end.
    """

    def __init__(self, cycle: list[str]) -> None:
        super().__init__("dependency cycle: " + " -> ".join(cycle))
        self.cycle = list(cycle)


def _edges(graph: dict[str, list[str]]) -> dict[str, set[str]]:
    """node -> its distinct dependencies, with implicit leaves filled in."""
    deps = {node: set(dependencies) for node, dependencies in graph.items()}
    for dependencies in list(deps.values()):
        for dep in dependencies:
            deps.setdefault(dep, set())
    return deps


def resolve(graph: dict[str, list[str]]) -> list[str]:
    """Return the build order of `graph`, dependencies first."""
    deps = _edges(graph)

    dependents: dict[str, list[str]] = {node: [] for node in deps}
    waiting = {node: len(dependencies) for node, dependencies in deps.items()}
    for node, dependencies in deps.items():
        for dep in dependencies:
            dependents[dep].append(node)

    ready = [node for node, count in waiting.items() if count == 0]
    heapq.heapify(ready)

    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dependent in dependents[node]:
            waiting[dependent] -= 1
            if waiting[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(deps):
        raise CycleError(_shortest_cycle(deps, set(deps) - set(order)))
    return order


def _shortest_cycle(deps: dict[str, set[str]], stuck: set[str]) -> list[str]:
    """The shortest cycle among `stuck`, rotated to start at its smallest member.

    Every cycle in the graph lies entirely inside `stuck` (a node is only left
    unemitted when it depends, transitively, on a cycle), so searching there
    loses nothing.
    """
    nodes = sorted(stuck)
    adj = {node: sorted(deps[node] & stuck) for node in nodes}

    for length in range(1, len(nodes) + 1):
        for start in nodes:
            # Intermediates are held above `start`, so whatever is found is
            # already rotated to begin at its smallest member. Neighbours are
            # walked in sorted order, so the first hit at a given length is the
            # lexicographically smallest cycle of that length.
            found = _walk(adj, start, [start], length)
            if found is not None:
                return found
    raise AssertionError("stuck nodes always contain a cycle")


def _walk(
    adj: dict[str, list[str]], start: str, path: list[str], length: int
) -> list[str] | None:
    if len(path) == length:
        return list(path) if start in adj[path[-1]] else None
    for nxt in adj[path[-1]]:
        if nxt <= start:  # keeps `start` the smallest member, and no repeats
            continue
        if nxt in path:
            continue
        path.append(nxt)
        found = _walk(adj, start, path, length)
        path.pop()
        if found is not None:
            return found
    return None
