"""Held-out tests. Never present in the workspace the agent works in.

Every input here is absent from tests/fixtures/cases.json, so an implementation
that replays the fixture has nothing to replay. Where an expectation can be
derived rather than transcribed it is: the round-trip tests build the input
line out of the words that must come back.

Tricky inputs are written as raw triple-quoted strings so that both quote
characters can appear verbatim; the few that need a real newline or a trailing
backslash are ordinary strings and are commented.
"""

import pytest

from src.wordsplit import SplitError, split


# --- concatenation of adjacent runs -----------------------------------------


def test_quoted_and_unquoted_runs_concatenate():
    assert split(r"""a"b c"d'e f'""") == ["ab cde f"]


def test_quote_styles_touching_make_one_word():
    assert split(r""""one"'two'three""") == ["onetwothree"]


def test_a_quote_does_not_end_the_word_it_sits_in():
    assert split(r"""--flag='some value' rest""") == ["--flag=some value", "rest"]


def test_reopening_a_quote_inside_a_word():
    assert split(r"""'a''b' c""") == ["ab", "c"]


# --- empty words -------------------------------------------------------------


def test_empty_single_quotes_make_an_empty_word():
    assert split(r"""x '' y""") == ["x", "", "y"]


def test_empty_double_quotes_make_an_empty_word():
    assert split(r"""p "" q""") == ["p", "", "q"]


def test_an_empty_quoted_string_alone_is_one_empty_word():
    assert split(r"""''""") == [""]
    assert split(r'''""''') == [""]


def test_two_empty_strings_touching_are_still_one_empty_word():
    assert split(r"""''""" + r'''""''') == [""]


def test_separators_only_produce_no_words():
    assert split("   \t  \t") == []


def test_empty_word_is_not_dropped_from_the_middle():
    got = split(r"""set -- '' end""")
    assert got == ["set", "--", "", "end"]
    assert len(got) == 4


# --- comments ----------------------------------------------------------------


def test_hash_after_a_separator_starts_a_comment():
    assert split("run fast # why not") == ["run", "fast"]


def test_hash_at_the_start_of_the_line_kills_everything():
    assert split("# nothing to see here") == []


def test_hash_inside_a_word_is_an_ordinary_character():
    assert split("a#b c#d") == ["a#b", "c#d"]


def test_hash_is_ordinary_when_quoted_or_escaped():
    assert split(r"""'#' "#" \#""") == ["#", "#", "#"]


def test_hash_right_after_a_quoted_run_is_ordinary():
    # The '' opens a word, so the # that follows is not word-initial.
    assert split(r"""''#kept""") == ["#kept"]


def test_comment_starts_a_word_that_never_opens():
    assert split(r"""keep "this" #and not this""") == ["keep", "this"]


# --- backslash inside double quotes -----------------------------------------


@pytest.mark.parametrize(
    "line,expected",
    [
        (r'''"a\$b"''', "a$b"),
        (r'''"a\`b"''', "a`b"),
        (r'''"a\\b"''', "a\\b"),
        (r'''"a\"b"''', 'a"b'),
        # not in the escapable set: the backslash stays
        (r'''"a\nb"''', "a\\nb"),
        (r'''"a\'b"''', "a\\'b"),
        (r'''"a\ b"''', "a\\ b"),
        (r'''"a\#b"''', "a\\#b"),
    ],
)
def test_double_quote_backslash_is_selective(line, expected):
    assert split(line) == [expected]


def test_escaped_double_quote_does_not_close_the_quoting():
    assert split(r'''"a \"b c\" d"''') == ['a "b c" d']


# --- backslash elsewhere -----------------------------------------------------


def test_backslash_is_literal_inside_single_quotes():
    assert split(r"""'\$ \n \\'""") == ["\\$ \\n \\\\"]


def test_single_quotes_end_at_the_first_quote_even_after_a_backslash():
    assert split("'x\\' y") == ["x\\", "y"]


def test_backslash_outside_quotes_escapes_anything():
    assert split(r"""\'a\' \"b\" \\c""") == ["'a'", '"b"', "\\c"]


def test_escaped_tab_joins_the_word():
    assert split("a\\\tb") == ["a\tb"]


# --- line continuation -------------------------------------------------------


def test_continuation_joins_two_halves_of_a_word():
    assert split("ab\\\ncd") == ["abcd"]  # ab, backslash, newline, cd


def test_continuation_does_not_open_a_word():
    assert split("x \\\n y") == ["x", "y"]


def test_continuation_inside_double_quotes():
    assert split('"ab\\\ncd"') == ["abcd"]


def test_a_bare_newline_is_an_ordinary_character():
    assert split("ab\ncd") == ["ab\ncd"]


# --- no expansions -----------------------------------------------------------


@pytest.mark.parametrize(
    "word",
    ["$HOME", "${HOME}", "$(pwd)", "`date`", "~", "*.py", "a{b,c}", "!!", "$?"],
)
def test_nothing_is_expanded(word):
    assert split(word) == [word]
    assert split('"' + word + '"') == [word]


def test_a_substitution_holding_a_space_is_still_two_words_unquoted():
    # No expansion happens, so $( ) is not a unit: the space separates.
    assert split("$(echo hi)") == ["$(echo", "hi)"]
    assert split(r'''"$(echo hi)"''') == ["$(echo hi)"]


# --- errors ------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "'",
        '"',
        "a 'b c",
        'a "b c',
        "trailing one\\",  # ends with a lone backslash
        "\\",
        '"open \\',  # backslash then end of input, inside double quotes
        "mix 'a\"b",
    ],
)
def test_rejects_unterminated_input(line):
    with pytest.raises(SplitError):
        split(line)


def test_escaped_quote_is_not_an_open_quote():
    assert split(r"""\' \" ok""") == ["'", '"', "ok"]


def test_error_type_is_a_value_error():
    assert issubclass(SplitError, ValueError)


# --- derived round trips (expectation built from the answer, not transcribed) -


ROUND_TRIP_WORDS = [
    "plain",
    "two words",
    "  padded  ",
    "$not expanded",
    "tab\there",
    "#hash",
    "",
    'has "double" quotes',
    "back\\slash",
]


def test_single_quoting_every_word_round_trips():
    line = " ".join("'" + w + "'" for w in ROUND_TRIP_WORDS)
    assert split(line) == ROUND_TRIP_WORDS


def test_backslash_escaping_every_character_round_trips():
    words = [w for w in ROUND_TRIP_WORDS if w]  # an empty word needs quotes
    line = " ".join("".join("\\" + c for c in w) for w in words)
    assert split(line) == words


def test_double_quoting_round_trips_when_the_word_is_escaped():
    escapable = set('$`"\\')
    words = [w for w in ROUND_TRIP_WORDS if "\n" not in w]
    line = " ".join(
        '"' + "".join(("\\" + c if c in escapable else c) for c in w) + '"'
        for w in words
    )
    assert split(line) == words
