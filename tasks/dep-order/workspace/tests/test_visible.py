import pytest

from src.deporder import CycleError, resolve


def test_empty_graph():
    assert resolve({}) == []


def test_single_node_without_dependencies():
    assert resolve({"a": []}) == ["a"]


def test_linear_chain():
    assert resolve({"c": ["b"], "b": ["a"], "a": []}) == ["a", "b", "c"]


def test_dependencies_come_first():
    graph = {"app": ["ui", "db"], "ui": ["core"], "db": ["core"], "core": []}
    order = resolve(graph)
    assert sorted(order) == ["app", "core", "db", "ui"]
    for node, deps in graph.items():
        for dep in deps:
            assert order.index(dep) < order.index(node)


def test_lexicographic_among_ready_roots():
    assert resolve({"b": [], "a": [], "c": []}) == ["a", "b", "c"]


def test_duplicate_dependencies_collapse():
    assert resolve({"b": ["a", "a"], "a": []}) == ["a", "b"]


def test_cycle_raises():
    with pytest.raises(CycleError):
        resolve({"a": ["b"], "b": ["a"]})


def test_cycle_error_is_a_value_error():
    assert issubclass(CycleError, ValueError)
