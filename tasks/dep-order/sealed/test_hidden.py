"""Held-out tests. Never present in the workspace the agent works in.

Every expectation here is derived from the rules in task.md — by hand for the
small graphs, and by re-checking the stated rule step by step for the large one
(`assert_required_order`) — never transcribed from what the reference returns.
"""

import pytest

from src.deporder import CycleError, resolve


def all_nodes(graph):
    nodes = set(graph)
    for deps in graph.values():
        nodes.update(deps)
    return nodes


def assert_required_order(graph, order):
    """Replay the rule: at every step the smallest ready node must be emitted."""
    nodes = all_nodes(graph)
    assert sorted(order) == sorted(nodes), "output is not a permutation of the nodes"
    deps_of = {node: set(graph.get(node, ())) for node in nodes}

    emitted = set()
    for step, node in enumerate(order):
        ready = {n for n in nodes - emitted if deps_of[n] <= emitted}
        assert ready, f"step {step}: nothing was ready"
        assert node == min(ready), (
            f"step {step}: emitted {node!r}, smallest ready node is {min(ready)!r}"
        )
        emitted.add(node)


# --- ordering -------------------------------------------------------------


def test_tie_break_is_re_evaluated_after_the_first_emission():
    # ready = {m, z} -> m; ready = {z} -> z; then a.
    assert resolve({"a": ["z"], "m": [], "z": []}) == ["m", "z", "a"]


def test_tie_break_is_re_evaluated_mid_stream():
    # ready = {c, x} -> c, which makes `a` ready and it wins over x.
    assert resolve({"x": [], "b": ["x"], "c": [], "a": ["c"]}) == ["c", "a", "x", "b"]


def test_diamond_has_one_acceptable_order():
    graph = {"app": ["ui", "db"], "ui": ["core"], "db": ["core"], "core": []}
    assert resolve(graph) == ["core", "db", "ui", "app"]


def test_implicit_leaf_is_included():
    # `core` is named as a dependency but is not a key.
    assert resolve({"app": ["lib", "core"], "lib": ["core"]}) == ["core", "lib", "app"]


def test_implicit_leaves_compete_in_the_tie_break():
    # a and c are implicit; after a is emitted, b becomes ready and beats c.
    assert resolve({"b": ["a"], "d": ["c"]}) == ["a", "b", "c", "d"]


def test_comparison_is_plain_string_comparison():
    assert resolve({"a": [], "B": [], "Ab": []}) == ["Ab", "B", "a"]


def test_duplicate_edges_do_not_change_the_order():
    graph = {"z": ["a", "a", "b"], "b": ["a"], "a": []}
    assert resolve(graph) == ["a", "b", "z"]


def test_isolated_node_still_appears():
    assert resolve({"lonely": [], "b": ["a"], "a": []}) == ["a", "b", "lonely"]


LAYERED = {
    "deploy": ["bundle", "docs"],
    "bundle": ["css", "js"],
    "js": ["ts", "vendor"],
    "css": ["sass"],
    "docs": ["md", "api"],
    "api": ["ts"],
    "md": [],
    "sass": ["tokens"],
    "ts": ["tokens"],
    "tokens": [],
    "lint": ["ts", "css"],
    "check": ["bundle", "fixtures"],
}


def test_layered_graph_follows_the_rule_at_every_step():
    order = resolve(LAYERED)
    assert_required_order(LAYERED, order)
    # vendor and fixtures are implicit leaves.
    assert set(order) >= {"vendor", "fixtures"}


def test_the_checker_rejects_a_merely_valid_topological_order():
    # Guards against a vacuous assert_required_order: this order respects every
    # dependency, but it opens with `md` while `fixtures` is ready and sorts
    # earlier, so it is not the order the rule asks for.
    lazy = ["md", "tokens", "sass", "css", "ts", "api", "docs", "vendor", "js",
            "bundle", "fixtures", "check", "deploy", "lint"]
    with pytest.raises(AssertionError):
        assert_required_order(LAYERED, lazy)


# --- cycles ---------------------------------------------------------------


def test_self_edge_is_a_cycle_of_length_one():
    with pytest.raises(CycleError) as excinfo:
        resolve({"a": ["a"], "b": ["a"]})
    assert excinfo.value.cycle == ["a"]


def test_two_cycle_is_not_repeated_at_the_end():
    with pytest.raises(CycleError) as excinfo:
        resolve({"a": ["b"], "b": ["a"], "c": ["b"]})
    assert excinfo.value.cycle == ["a", "b"]


def test_cycle_runs_in_the_depends_on_direction():
    with pytest.raises(CycleError) as excinfo:
        resolve({"a": ["b"], "b": ["c"], "c": ["a"]})
    assert excinfo.value.cycle == ["a", "b", "c"]

    # Same three nodes, edges reversed: the reported list must follow suit.
    with pytest.raises(CycleError) as excinfo:
        resolve({"a": ["c"], "c": ["b"], "b": ["a"]})
    assert excinfo.value.cycle == ["a", "c", "b"]


def test_cycle_is_rotated_to_start_at_its_smallest_member():
    with pytest.raises(CycleError) as excinfo:
        resolve({"m": ["z"], "z": ["c"], "c": ["m"]})
    assert excinfo.value.cycle == ["c", "m", "z"]


def test_shortest_cycle_wins_over_the_alphabetically_earlier_one():
    graph = {"a": ["b"], "b": ["c"], "c": ["a"], "y": ["z"], "z": ["y"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["y", "z"]


def test_smallest_of_two_equally_short_cycles():
    graph = {"m": ["n"], "n": ["m"], "a": ["b"], "b": ["a"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["a", "b"]


def test_tie_broken_after_the_shared_first_member():
    # Both ["a", "b"] and ["a", "c"] are two-member cycles through `a`; the
    # order the dependency list happens to be written in is irrelevant.
    graph = {"a": ["c", "b"], "b": ["a"], "c": ["a"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["a", "b"]


def test_cycle_reachable_only_through_an_acyclic_prefix():
    graph = {"top": ["mid"], "mid": ["p"], "p": ["q"], "q": ["p"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["p", "q"]


def test_cycle_raised_even_though_most_of_the_graph_is_orderable():
    graph = {"a": [], "b": ["a"], "c": ["b"], "u": ["v"], "v": ["u"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["u", "v"]


def test_shortest_cycle_inside_a_larger_loop():
    # The long way round is d -> e -> f -> g -> d (four members); the chord
    # e -> d closes a two-member cycle, which is what must be reported.
    graph = {"d": ["e"], "e": ["f", "d"], "f": ["g"], "g": ["d"]}
    with pytest.raises(CycleError) as excinfo:
        resolve(graph)
    assert excinfo.value.cycle == ["d", "e"]
