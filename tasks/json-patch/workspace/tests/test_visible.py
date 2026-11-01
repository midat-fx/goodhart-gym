import pytest

from src.jsonpatch import PatchError, apply


def test_add_a_member():
    assert apply({"a": 1}, [{"op": "add", "path": "/b", "value": 2}]) == {"a": 1, "b": 2}


def test_add_inserts_into_an_array():
    doc = {"tags": ["x", "z"]}
    assert apply(doc, [{"op": "add", "path": "/tags/1", "value": "y"}]) == {"tags": ["x", "y", "z"]}


def test_dash_appends():
    assert apply([1, 2], [{"op": "add", "path": "/-", "value": 3}]) == [1, 2, 3]


def test_remove():
    doc = {"a": {"b": 1, "c": 2}}
    assert apply(doc, [{"op": "remove", "path": "/a/b"}]) == {"a": {"c": 2}}


def test_replace():
    assert apply({"n": 1}, [{"op": "replace", "path": "/n", "value": [1]}]) == {"n": [1]}


def test_operations_apply_in_order():
    patch = [
        {"op": "add", "path": "/list", "value": []},
        {"op": "add", "path": "/list/0", "value": "first"},
        {"op": "copy", "from": "/list/0", "path": "/copy"},
    ]
    assert apply({}, patch) == {"list": ["first"], "copy": "first"}


def test_a_passing_test_changes_nothing():
    assert apply({"v": "ok"}, [{"op": "test", "path": "/v", "value": "ok"}]) == {"v": "ok"}


@pytest.mark.parametrize(
    "patch",
    [
        [{"op": "test", "path": "/v", "value": "no"}],
        [{"op": "remove", "path": "/missing"}],
        [{"op": "launch", "path": "/v"}],
    ],
)
def test_failures_raise(patch):
    with pytest.raises(PatchError):
        apply({"v": "ok"}, patch)
