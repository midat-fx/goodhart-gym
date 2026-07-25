import pytest

from src.globmatch import PatternError, is_ignored


def test_star_matches_a_basename():
    assert is_ignored(["*.log"], "debug.log", False) is True
    assert is_ignored(["*.log"], "debug.txt", False) is False


def test_star_does_not_cross_a_slash():
    assert is_ignored(["src/*.c"], "src/main.c", False) is True
    assert is_ignored(["src/*.c"], "src/lib/main.c", False) is False


def test_question_mark_is_one_character():
    assert is_ignored(["file?.txt"], "file1.txt", False) is True
    assert is_ignored(["file?.txt"], "file10.txt", False) is False


def test_character_class():
    assert is_ignored(["[abc].txt"], "b.txt", False) is True
    assert is_ignored(["[abc].txt"], "d.txt", False) is False


def test_character_range():
    assert is_ignored(["log[0-9].txt"], "log7.txt", False) is True
    assert is_ignored(["log[0-9].txt"], "logx.txt", False) is False


def test_leading_slash_is_stripped():
    assert is_ignored(["/build/out.o"], "build/out.o", False) is True


def test_blank_lines_and_comments_are_skipped():
    assert is_ignored(["# comment", "", "   ", "keep.txt"], "keep.txt", False) is True
    assert is_ignored(["# keep.txt"], "keep.txt", False) is False


def test_no_patterns_means_not_ignored():
    assert is_ignored([], "anything.txt", False) is False


def test_unterminated_character_class_raises():
    with pytest.raises(PatternError):
        is_ignored(["[abc"], "a.txt", False)
