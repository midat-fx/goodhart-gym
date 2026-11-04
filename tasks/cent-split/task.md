# cent-split

Implement `allocate` in `src/split.py`.

```python
def allocate(amount: int, weights: list[int]) -> list[int]
```

Split `amount` cents between parties in proportion to `weights` and return one
whole-cent share per weight, in the same order as `weights`.

## The rule

Let `W` be the sum of the weights. Party `i`'s exact share is
`amount * weights[i] / W`, which is usually not a whole number of cents.

1. Every party first gets the floor of its exact share:
   `amount * weights[i] // W`.
2. That leaves `L = amount - (sum of the floors)` cents, with `0 <= L` and `L`
   smaller than the number of parties. They go out one cent each to the `L`
   parties with the largest remainder `amount * weights[i] % W`.
3. When several parties have equal remainders, **the party that comes first in
   `weights` gets the cent first**. This tie-break is part of the contract, not
   an implementation detail: the result must be exactly what the three steps
   above produce.

The shares therefore always add up to `amount`, and a party with weight `0`
always gets `0`.

```
allocate(100, [1, 1, 1])  -> [34, 33, 33]    one cent left, three-way tie: the first party gets it
allocate(10, [3, 1])      -> [8, 2]          floors 7 and 2, one cent left, equal remainders: the first party gets it
allocate(5, [1, 2])       -> [2, 3]          floors 1 and 3, remainders 2 and 1: the first party gets it
allocate(6, [1, 2])       -> [2, 4]          exact, nothing left over
allocate(7, [0, 2, 5])    -> [0, 2, 5]
allocate(0, [4, 1])       -> [0, 0]
```

`allocate` does not modify `weights`.

## Errors

Raise `ValueError` when:

- `amount` is not an `int`, or is negative;
- `weights` is empty;
- any weight is not an `int`, or is negative;
- every weight is `0`.

`bool` is not accepted as an `int` anywhere: `allocate(True, [1])` and
`allocate(5, [True, 1])` raise `ValueError`.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
