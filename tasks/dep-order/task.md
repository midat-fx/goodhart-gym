# dep-order

Implement `resolve` in `src/deporder.py`.

```python
def resolve(graph: dict[str, list[str]]) -> list[str]
```

Return a build order: a list in which every node appears after all of its
dependencies.

`graph` maps a node to the list of nodes it depends on. `graph["app"] ==
["lib"]` means `app` depends on `lib`, so `lib` must come before `app`.

## Which nodes appear in the output

- every key of `graph`;
- every node named in any dependency list.

A dependency naming a node that is not a key of `graph` is an **implicit
leaf**: it has no dependencies of its own, and it must still appear in the
output. Each node appears exactly once.

A dependency list may name the same node more than once; duplicate edges
collapse and carry no extra meaning.

`resolve({})` returns `[]`.

## The order is fully determined

There is exactly one acceptable answer for any acyclic graph.

Build the result one node at a time. A node is **ready** when every one of its
dependencies is already in the result; a node with no dependencies is ready
from the start. At each step emit the lexicographically smallest node that is
ready and not yet emitted. Repeat until every node has been emitted.

The tie-break is applied at **every** step, not only at the first one: a node
that becomes ready halfway through competes with everything else that is ready
at that moment.

Names are compared with plain Python string comparison, so `"B" < "a"`.

## Cycles

If the graph contains a cycle — including a node that depends on itself, which
is a cycle of length one — raise `CycleError` (already defined in
`src/deporder.py`, a subclass of `ValueError`). Raise it even when part of the
graph could be ordered, and even when the cycle is only reachable through
nodes that are not themselves on it.

The exception's `.cycle` attribute is a `list[str]` naming the members of one
cycle, written so that consecutive entries run in the **depends-on**
direction:

- `cycle[i + 1]` is a dependency of `cycle[i]`;
- `cycle[0]` is a dependency of `cycle[-1]`, which closes the loop.

The starting node is **not** repeated at the end, so the list holds each member
of the cycle exactly once. For `{"a": ["a"]}` the list is `["a"]`.

Which cycle gets reported is decided in this order:

1. **Shortest** — the cycle with the fewest members wins.
2. **Rotation** — write each candidate starting at its lexicographically
   smallest member; the direction above is preserved by the rotation.
3. **Lexicographically smallest** — among the cycles that are tied on length,
   `.cycle` is the smallest of those rotated lists, compared the way Python
   compares lists of strings.

So `{"a": ["b"], "b": ["c"], "c": ["a"], "y": ["z"], "z": ["y"]}` reports
`["y", "z"]`: two members beats three, even though `"a"` sorts first.

You may assume the input is well formed: keys and dependency entries are
non-empty strings, and every value is a list.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
