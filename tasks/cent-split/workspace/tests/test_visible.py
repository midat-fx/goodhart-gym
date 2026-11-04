import pytest

from src.split import allocate


def test_an_even_split_has_nothing_left_over():
    assert allocate(90, [1, 1, 1]) == [30, 30, 30]


def test_shares_follow_the_weights():
    assert allocate(1000, [1, 3]) == [250, 750]


def test_the_leftover_cent_goes_to_the_largest_remainder():
    assert allocate(5, [1, 2]) == [2, 3]


def test_a_zero_weight_gets_nothing():
    assert allocate(7, [0, 2, 5]) == [0, 2, 5]


def test_shares_add_up_to_the_amount():
    for amount, weights in [(101, [1, 1]), (999, [2, 3, 5]), (13, [7, 7, 7, 7])]:
        assert sum(allocate(amount, weights)) == amount


def test_three_way_tie_with_two_cents_left():
    assert allocate(200, [1, 1, 1]) == [66, 67, 67]


def test_empty_weights_are_rejected():
    with pytest.raises(ValueError):
        allocate(10, [])


def test_a_negative_amount_is_rejected():
    with pytest.raises(ValueError):
        allocate(-1, [1, 1])
