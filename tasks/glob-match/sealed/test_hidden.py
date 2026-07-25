"""Held-out tests. Never present in the workspace the agent works in.

Expectations are derived from the rules in task.md — depth families are
generated from the rule they illustrate rather than transcribed one by one.
"""

import pytest

from src.globmatch import PatternError, is_ignored


def nest(depth: int, name: str) -> str:
    """`nest(2, "x")` -> "d0/d1/x"."""
    return "/".join([f"d{i}" for i in range(depth)] + [name])


# --------------------------------------------------------- last match wins


def test_negation_after_a_match_unignores():
    assert is_ignored(["*.log", "!keep.log"], "a/b/keep.log", False) is False
    assert is_ignored(["*.log", "!keep.log"], "a/b/other.log", False) is True


def test_negation_before_a_match_is_overridden():
    assert is_ignored(["!keep.log", "*.log"], "a/b/keep.log", False) is True


def test_only_the_last_matching_pattern_counts():
    # All three match "x.a"; the last one decides.
    assert is_ignored(["*.a", "!x.a", "x.*"], "x.a", False) is True
    assert is_ignored(["x.*", "*.a", "!x.a"], "x.a", False) is False


def test_negation_alone_never_ignores():
    assert is_ignored(["!*.log"], "a.log", False) is False


def test_reincluding_inside_an_ignored_directory_works():
    # There is no parent-directory rule: the file's own last match decides.
    rules = ["build/**", "!build/keep.txt"]
    assert is_ignored(rules, "build/keep.txt", False) is False
    assert is_ignored(rules, "build/other.txt", False) is True


def test_result_is_a_bool():
    assert is_ignored(["*.log"], "a.log", False) is True
    assert is_ignored(["*.log"], "a.txt", False) is False


# ------------------------------------------------ no slash means any depth


def test_slashless_pattern_matches_basename_at_every_depth():
    for depth in range(5):
        assert is_ignored(["config.json"], nest(depth, "config.json"), False) is True
        assert is_ignored(["*.o"], nest(depth, "x.o"), False) is True


def test_slashless_pattern_matches_the_basename_only():
    assert is_ignored(["config.json"], "a/config.json.bak", False) is False
    assert is_ignored(["config.json"], "config.json/x", False) is False
    assert is_ignored(["b"], "b/c", False) is False


def test_leading_slash_anchors_to_the_root():
    assert is_ignored(["/config.json"], "config.json", False) is True
    for depth in range(1, 4):
        assert is_ignored(["/config.json"], nest(depth, "config.json"), False) is False


def test_internal_slash_anchors_to_the_root():
    assert is_ignored(["a/b"], "a/b", False) is True
    assert is_ignored(["a/b"], "x/a/b", False) is False
    assert is_ignored(["src/*.c"], "src/main.c", False) is True
    assert is_ignored(["src/*.c"], "lib/src/main.c", False) is False


# -------------------------------------------------------- directory-only


def test_directory_only_needs_is_dir():
    assert is_ignored(["build/"], "build", True) is True
    assert is_ignored(["build/"], "build", False) is False


def test_directory_only_does_not_ignore_the_contents():
    assert is_ignored(["build/"], "build/out.o", False) is False
    assert is_ignored(["build/"], "build/sub", True) is False


def test_directory_only_still_matches_at_any_depth():
    # The trailing "/" is removed before anchoring is decided, so "build/"
    # has no slash left and stays a basename pattern.
    for depth in range(4):
        assert is_ignored(["build/"], nest(depth, "build"), True) is True
    assert is_ignored(["/build/"], "build", True) is True
    assert is_ignored(["/build/"], "a/build", True) is False


def test_directory_only_negation():
    rules = ["tmp/", "!a/tmp/"]
    assert is_ignored(rules, "a/tmp", True) is False
    assert is_ignored(rules, "b/tmp", True) is True
    assert is_ignored(rules, "a/tmp", False) is False


def test_plain_pattern_matches_directories_too():
    assert is_ignored(["build"], "build", True) is True
    assert is_ignored(["build"], "build", False) is True


# ------------------------------------------------------------ ** segments


def test_leading_doublestar_matches_at_any_depth():
    for depth in range(4):
        path = "/".join([f"d{i}" for i in range(depth)] + ["foo", "bar"])
        assert is_ignored(["**/foo/bar"], path, False) is True
    assert is_ignored(["**/foo/bar"], "foo/x/bar", False) is False


def test_middle_doublestar_spans_zero_or_more_segments():
    for extra in range(4):
        path = "/".join(["a"] + [f"m{i}" for i in range(extra)] + ["b"])
        assert is_ignored(["a/**/b"], path, False) is True
    assert is_ignored(["a/**/b"], "b", False) is False
    assert is_ignored(["a/**/b"], "a/b/c", False) is False
    assert is_ignored(["a/**/b"], "x/a/b", False) is False


def test_trailing_doublestar_needs_at_least_one_segment():
    assert is_ignored(["abc/**"], "abc", True) is False
    assert is_ignored(["abc/**"], "abc", False) is False
    for depth in range(1, 4):
        path = "abc/" + "/".join(f"d{i}" for i in range(depth))
        assert is_ignored(["abc/**"], path, False) is True


def test_doublestar_inside_a_segment_is_a_plain_star():
    assert is_ignored(["a**b"], "axxb", False) is True
    assert is_ignored(["a**b"], "ab", False) is True
    assert is_ignored(["a**b"], "a/x/b", False) is False
    assert is_ignored(["x/a**b"], "x/a/y/b", False) is False


def test_star_never_crosses_a_slash():
    assert is_ignored(["/*"], "a", False) is True
    assert is_ignored(["/*"], "a/b", False) is False
    assert is_ignored(["a/*/c"], "a/b/c", False) is True
    assert is_ignored(["a/*/c"], "a/b/x/c", False) is False


# ------------------------------------------------------- character classes


def test_negated_class():
    assert is_ignored(["[!0-9].txt"], "a.txt", False) is True
    assert is_ignored(["[!0-9].txt"], "1.txt", False) is False


def test_caret_is_an_ordinary_class_member():
    assert is_ignored(["[^a]"], "^", False) is True
    assert is_ignored(["[^a]"], "a", False) is True
    assert is_ignored(["[^a]"], "b", False) is False


def test_bracket_first_and_dash_last_are_ordinary_members():
    assert is_ignored(["[]x]"], "]", False) is True
    assert is_ignored(["[]x]"], "x", False) is True
    assert is_ignored(["[]x]"], "y", False) is False
    assert is_ignored(["[a-]"], "-", False) is True
    assert is_ignored(["[a-]"], "a", False) is True
    assert is_ignored(["[a-]"], "b", False) is False


def test_class_matches_exactly_one_character():
    assert is_ignored(["[abc][abc]"], "ab", False) is True
    assert is_ignored(["[abc][abc]"], "a", False) is False
    assert is_ignored(["[abc][abc]"], "abc", False) is False


# ------------------------------------------------- escapes and line reading


def test_escaped_bang_is_a_literal():
    assert is_ignored(["\\!important.txt"], "!important.txt", False) is True
    # Unescaped, the same line negates the pattern "important.txt".
    assert is_ignored(["!important.txt"], "!important.txt", False) is False


def test_escaped_hash_is_a_literal():
    assert is_ignored(["\\#tag"], "#tag", False) is True
    assert is_ignored(["#tag"], "#tag", False) is False


def test_escaped_wildcards_are_literals():
    assert is_ignored(["a\\*b"], "a*b", False) is True
    assert is_ignored(["a\\*b"], "axxb", False) is False
    assert is_ignored(["a\\?b"], "a?b", False) is True
    assert is_ignored(["a\\?b"], "axb", False) is False
    assert is_ignored(["\\[abc]"], "[abc]", False) is True


def test_trailing_spaces_are_stripped_unless_escaped():
    assert is_ignored(["doc "], "doc", False) is True
    assert is_ignored(["doc   "], "doc", False) is True
    assert is_ignored(["doc\\ "], "doc ", False) is True
    assert is_ignored(["doc\\ "], "doc", False) is False


def test_lines_that_disappear_are_ignored():
    for line in ["", "   ", "#", "# *", "!", "/"]:
        assert is_ignored([line], "anything", False) is False
        assert is_ignored([line], "a/b", True) is False


def test_matching_is_case_sensitive():
    assert is_ignored(["*.LOG"], "a.log", False) is False
    assert is_ignored(["README"], "readme", False) is False


# ------------------------------------------------------------------ errors


@pytest.mark.parametrize(
    "pattern",
    [
        "[abc",  # unterminated
        "[a-b",  # unterminated after a range
        "[]",  # the "]" is an ordinary member, so still unterminated
        "[z-a]",  # reversed range
        "[9-0]",
        "a[/]c",  # a class may not span a "/"
        "foo\\",  # dangling escape
        "a/b\\",
        "[a\\",
    ],
)
def test_malformed_patterns_raise(pattern):
    with pytest.raises(PatternError):
        is_ignored([pattern], "x", False)


def test_every_line_is_compiled_before_matching():
    # "*.log" already decided the answer; the bad line still raises.
    with pytest.raises(PatternError):
        is_ignored(["*.log", "[z-a]"], "x.log", False)
    with pytest.raises(PatternError):
        is_ignored(["[z-a]", "*.log"], "x.log", False)


def test_skipped_lines_are_never_compiled():
    assert is_ignored(["#[abc", "keep"], "keep", False) is True
    assert is_ignored(["", "   ", "#\\"], "keep", False) is False


def test_pattern_error_is_a_valueerror():
    assert issubclass(PatternError, ValueError)
