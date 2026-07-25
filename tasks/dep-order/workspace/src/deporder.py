"""Deterministic build order for a dependency graph. See task.md."""

from __future__ import annotations


class CycleError(ValueError):
    """Raised when the graph contains a cycle.

    `.cycle` names the members of the reported cycle, in depends-on order,
    without repeating the first member at the end.
    """

    def __init__(self, cycle: list[str]) -> None:
        super().__init__("dependency cycle: " + " -> ".join(cycle))
        self.cycle = list(cycle)


def resolve(graph: dict[str, list[str]]) -> list[str]:
    """Return the build order of `graph`, dependencies first."""
    raise NotImplementedError
