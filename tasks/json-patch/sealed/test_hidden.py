"""Held-out tests for json-patch, each derived from a rule in task.md."""

import copy

import pytest

from src.jsonpatch import PatchError, apply


def ok(doc, *ops):
    return apply(doc, list(ops))


def bad(doc, *ops):
    with pytest.raises(PatchError):
        apply(doc, list(ops))


# --- pointers -----------------------------------------------------------------

ESCAPED = {"a/b": 1, "m~n": 2, "": 3, " ": 4, "~1": 5, "-": 6}


@pytest.mark.parametrize(
    "path, value",
    [("/a~1b", 1), ("/m~0n", 2), ("/", 3), ("/ ", 4), ("/~01", 5), ("/-", 6)],
)
def test_pointer_escapes(path, value):
    assert ok(ESCAPED, {"op": "test", "path": path, "value": value}) == ESCAPED


@pytest.mark.parametrize("path", ["/a~2", "/a~", "a", "/~", "/x~y"])
def test_malformed_pointers(path):
    bad({"a": 1, "a~": 2}, {"op": "add", "path": path, "value": 0})


def test_dash_is_a_member_name_in_an_object():
    assert ok({}, {"op": "add", "path": "/-", "value": 1}) == {"-": 1}


@pytest.mark.parametrize("token", ["01", "-1", "1.0", " 1", "+1", "1 ", "x", "１"])
def test_bad_array_indexes(token):
    bad([10, 20, 30], {"op": "replace", "path": f"/{token}", "value": 0})
    bad([10, 20, 30], {"op": "add", "path": f"/{token}", "value": 0})


def test_cannot_descend_into_a_scalar():
    bad({"a": 1}, {"op": "add", "path": "/a/b", "value": 2})
    bad({"a": "text"}, {"op": "test", "path": "/a/0", "value": "t"})
    bad({"a": None}, {"op": "remove", "path": "/a/x"})


# --- add ------------------------------------------------------------------------


def test_add_at_the_length_appends():
    assert ok([1, 2], {"op": "add", "path": "/2", "value": 3}) == [1, 2, 3]
    assert ok([], {"op": "add", "path": "/0", "value": "x"}) == ["x"]


def test_add_past_the_length_is_an_error():
    bad([1, 2], {"op": "add", "path": "/3", "value": 3})


def test_add_replaces_an_existing_member():
    assert ok({"a": 1}, {"op": "add", "path": "/a", "value": 2}) == {"a": 2}


def test_add_needs_an_existing_parent():
    bad({}, {"op": "add", "path": "/a/b", "value": 1})
    bad({"a": []}, {"op": "add", "path": "/a/0/b", "value": 1})


def test_add_an_array_as_a_single_element():
    got = ok({"foo": ["bar"]}, {"op": "add", "path": "/foo/-", "value": ["abc", "def"]})
    assert got == {"foo": ["bar", ["abc", "def"]]}


def test_add_null_is_a_value():
    assert ok({}, {"op": "add", "path": "/a", "value": None}) == {"a": None}


def test_add_and_replace_the_whole_document():
    assert ok({"a": 1}, {"op": "add", "path": "", "value": [1]}) == [1]
    assert ok([1], {"op": "replace", "path": "", "value": "s"}) == "s"
    assert ok(3, {"op": "replace", "path": "", "value": {"x": 1}}) == {"x": 1}


# --- remove and replace -----------------------------------------------------------


def test_remove_shifts_an_array_down():
    assert ok([1, 2, 3], {"op": "remove", "path": "/0"}) == [2, 3]


def test_remove_errors():
    bad([1, 2], {"op": "remove", "path": "/2"})
    bad([1, 2], {"op": "remove", "path": "/-"})
    bad({"a": 1}, {"op": "remove", "path": ""})


def test_replace_must_exist():
    bad({}, {"op": "replace", "path": "/a", "value": 1})
    bad([1], {"op": "replace", "path": "/1", "value": 1})
    bad([1], {"op": "replace", "path": "/-", "value": 1})


def test_replace_in_an_array():
    assert ok([1, 2, 3], {"op": "replace", "path": "/1", "value": 9}) == [1, 9, 3]


# --- move and copy ------------------------------------------------------------------


def test_move_a_member():
    doc = {"foo": {"bar": "baz", "waldo": "fred"}, "qux": {"corge": "grault"}}
    got = ok(doc, {"op": "move", "from": "/foo/waldo", "path": "/qux/thud"})
    assert got == {"foo": {"bar": "baz"}, "qux": {"corge": "grault", "thud": "fred"}}


def test_move_reads_the_target_index_after_the_removal():
    doc = {"foo": ["all", "grass", "cows", "eat"]}
    got = ok(doc, {"op": "move", "from": "/foo/1", "path": "/foo/3"})
    assert got == {"foo": ["all", "cows", "eat", "grass"]}
    assert ok([1, 2, 3], {"op": "move", "from": "/0", "path": "/2"}) == [2, 3, 1]
    assert ok([1, 2, 3], {"op": "move", "from": "/0", "path": "/-"}) == [2, 3, 1]


def test_move_into_its_own_child_is_an_error():
    bad({"a": {"b": {}}}, {"op": "move", "from": "/a", "path": "/a/b"})
    bad({"a": {"b": {}}}, {"op": "move", "from": "/a", "path": "/a/b/c"})
    bad({"a": 1}, {"op": "move", "from": "", "path": "/b"})


def test_move_to_a_sibling_that_shares_a_prefix():
    assert ok({"a": 1}, {"op": "move", "from": "/a", "path": "/ab"}) == {"ab": 1}


def test_move_to_itself_changes_nothing():
    assert ok({"a": [1]}, {"op": "move", "from": "/a", "path": "/a"}) == {"a": [1]}
    bad({"a": [1]}, {"op": "move", "from": "/b", "path": "/b"})


def test_move_needs_an_existing_source():
    bad({"a": 1}, {"op": "move", "from": "/b", "path": "/c"})


def test_copy_is_deep():
    patch = [
        {"op": "copy", "from": "/a", "path": "/b"},
        {"op": "add", "path": "/b/x/-", "value": 2},
    ]
    assert apply({"a": {"x": [1]}}, patch) == {"a": {"x": [1]}, "b": {"x": [1, 2]}}


def test_copy_to_the_end_of_an_array():
    assert ok({"a": [1], "v": 2}, {"op": "copy", "from": "/v", "path": "/a/-"}) == {"a": [1, 2], "v": 2}


# --- test -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "actual, value",
    [
        (1, 1.0),
        (0, -0.0),
        ({"a": [1, {"b": 2}]}, {"a": [1.0, {"b": 2.0}]}),
        ({"x": 1, "y": 2}, {"y": 2, "x": 1}),
        (None, None),
        ("", ""),
        ([], []),
    ],
    ids=repr,
)
def test_equal_values(actual, value):
    ok({"v": actual}, {"op": "test", "path": "/v", "value": value})


@pytest.mark.parametrize(
    "actual, value",
    [
        (True, 1),
        (1, True),
        (False, 0),
        (0.0, False),
        (None, False),
        ("1", 1),
        ([True], [1]),
        ({"a": False}, {"a": 0}),
        ([1, 2], [2, 1]),
        ({"a": 1}, {"a": 1, "b": None}),
        ([1], [1, 1]),
        ({}, []),
    ],
    ids=repr,
)
def test_unequal_values(actual, value):
    bad({"v": actual}, {"op": "test", "path": "/v", "value": value})


def test_test_needs_an_existing_target():
    bad({"a": 1}, {"op": "test", "path": "/b", "value": None})
    bad([1], {"op": "test", "path": "/-", "value": 1})


# --- shape of the patch -----------------------------------------------------------


@pytest.mark.parametrize(
    "patch",
    [
        {"op": "add", "path": "/a", "value": 1},
        [["add", "/a", 1]],
        [{"path": "/a", "value": 1}],
        [{"op": 1, "path": "/a"}],
        [{"op": "ADD", "path": "/a", "value": 1}],
        [{"op": "add", "value": 1}],
        [{"op": "add", "path": 3, "value": 1}],
        [{"op": "add", "path": "/a"}],
        [{"op": "replace", "path": "/x"}],
        [{"op": "test", "path": "/x"}],
        [{"op": "move", "path": "/a"}],
        [{"op": "copy", "path": "/a", "from": None}],
    ],
    ids=repr,
)
def test_malformed_patches(patch):
    with pytest.raises(PatchError):
        apply({"x": 1}, patch)


def test_extra_members_are_ignored():
    got = ok({}, {"op": "add", "path": "/a", "value": 1, "from": 12, "comment": "hi"})
    assert got == {"a": 1}


def test_an_empty_patch_returns_an_equal_document():
    assert apply({"a": [1]}, []) == {"a": [1]}


# --- the inputs are never touched ----------------------------------------------------


def test_a_failed_patch_leaves_the_document_alone():
    doc = {"a": [1], "b": {"c": 2}}
    before = copy.deepcopy(doc)
    bad(
        doc,
        {"op": "add", "path": "/a/-", "value": 2},
        {"op": "remove", "path": "/b/c"},
        {"op": "test", "path": "/a/0", "value": 99},
    )
    assert doc == before


def test_a_successful_patch_leaves_the_inputs_alone():
    doc = {"a": [1], "b": {"c": 2}}
    patch = [
        {"op": "add", "path": "/a/-", "value": {"new": [1]}},
        {"op": "move", "from": "/b/c", "path": "/d"},
        {"op": "replace", "path": "/b", "value": []},
    ]
    doc_before, patch_before = copy.deepcopy(doc), copy.deepcopy(patch)
    assert apply(doc, patch) == {"a": [1, {"new": [1]}], "b": [], "d": 2}
    assert doc == doc_before
    assert patch == patch_before


def test_the_result_shares_nothing_with_the_inputs():
    doc = {"keep": {"deep": [1]}, "a": []}
    value = {"v": [1]}
    got = apply(doc, [{"op": "add", "path": "/a/-", "value": value}])
    got["keep"]["deep"].append(2)
    got["a"][0]["v"].append(2)
    assert doc == {"keep": {"deep": [1]}, "a": []}
    assert value == {"v": [1]}

    whole = {"x": [1]}
    got = apply({}, [{"op": "replace", "path": "", "value": whole}])
    got["x"].append(2)
    assert whole == {"x": [1]}

    untouched = {"x": [1]}
    got = apply(untouched, [])
    got["x"].append(2)
    assert untouched == {"x": [1]}
