"""Largest-remainder allocation of an amount in cents. See task.md."""

from __future__ import annotations


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def allocate(amount: int, weights: list[int]) -> list[int]:
    """Split `amount` cents in proportion to `weights`, one share per weight."""
    if not _is_int(amount) or amount < 0:
        raise ValueError(f"amount must be a non-negative int, got {amount!r}")
    if not weights:
        raise ValueError("weights must not be empty")
    for w in weights:
        if not _is_int(w) or w < 0:
            raise ValueError(f"every weight must be a non-negative int, got {w!r}")
    total = sum(weights)
    if total == 0:
        raise ValueError("at least one weight must be positive")

    shares = [amount * w // total for w in weights]
    left = amount - sum(shares)
    # Largest remainder first; equal remainders in the order the parties came.
    order = sorted(range(len(weights)), key=lambda i: (-(amount * weights[i] % total), i))
    for i in order[:left]:
        shares[i] += 1
    return shares
