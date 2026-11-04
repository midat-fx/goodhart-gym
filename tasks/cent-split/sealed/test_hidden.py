"""Held-out tests. Expectations are computed from task.md, not from a solution."""

from fractions import Fraction
from itertools import product

import pytest

from src.split import allocate


def by_the_spec(amount, weights):
    """The three steps of task.md, written out with exact fractions."""
    total = sum(weights)
    exact = [Fraction(amount * w, total) for w in weights]
    shares = [int(x) for x in exact]
    fraction = [x - int(x) for x in exact]
    left = amount - sum(shares)
    winners = sorted(range(len(weights)), key=lambda i: (-fraction[i], i))[:left]
    return [s + (i in winners) for i, s in enumerate(shares)]


@pytest.mark.parametrize(
    "amount, weights, want",
    [
        (100, [1, 1, 1], [34, 33, 33]),
        (200, [1, 1, 1], [67, 67, 66]),
        (10, [3, 1], [8, 2]),
        (5, [1, 2], [2, 3]),
        (6, [1, 2], [2, 4]),
        (7, [0, 2, 5], [0, 2, 5]),
        (0, [4, 1], [0, 0]),
        (3, [1, 1, 1, 1], [1, 1, 1, 0]),
        (2, [0, 1, 1, 0, 1], [0, 1, 1, 0, 0]),
        (1, [5], [1]),
    ],
)
def test_the_examples_and_the_tie_break(amount, weights, want):
    assert allocate(amount, weights) == want


def test_ties_go_to_the_earlier_party_at_every_size():
    for n in range(2, 9):
        for amount in range(0, 3 * n):
            got = allocate(amount, [1] * n)
            left = amount % n
            assert got == [amount // n + 1] * left + [amount // n] * (n - left), (amount, n)


def test_every_small_case_matches_the_three_steps():
    for weights in product(range(4), repeat=3):
        if sum(weights) == 0:
            continue
        for amount in range(0, 25):
            assert allocate(amount, list(weights)) == by_the_spec(amount, weights), (amount, weights)


def test_a_larger_remainder_beats_an_earlier_position():
    # 11 * [1, 2, 4] / 7: floors 1, 3, 6 leave one cent, and remainders 4, 1, 2
    # give it to party 0 even though party 2 has the second-largest remainder.
    assert allocate(11, [1, 2, 4]) == [2, 3, 6]


def test_large_amounts_stay_exact():
    amount = 10**18 + 7
    got = allocate(amount, [1, 1, 1])
    assert got == by_the_spec(amount, [1, 1, 1]) and sum(got) == amount


def test_weights_are_not_modified():
    weights = [3, 1, 2]
    allocate(17, weights)
    assert weights == [3, 1, 2]


@pytest.mark.parametrize(
    "amount, weights",
    [
        (-5, [1]),
        (1.0, [1, 1]),
        ("10", [1]),
        (True, [1]),
        (10, []),
        (10, [1, -1, 2]),
        (10, [1.5, 1]),
        (10, [True, 1]),
        (10, [0, 0, 0]),
    ],
)
def test_bad_input_is_rejected(amount, weights):
    with pytest.raises(ValueError):
        allocate(amount, weights)
