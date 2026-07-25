"""The schedule a retrying client would follow. See task.md."""

from __future__ import annotations

# A recorded response: {"status": int, "retry_after_ms": int}  (the second key
# is optional).
Response = dict

# A planned attempt: {"number": int, "start_ms": int, "delay_ms": int}.
Attempt = dict

SUCCESS = 200
RETRYABLE = frozenset({429, 500, 502, 503})


class PolicyError(ValueError):
    """Raised for a policy or deadline that cannot describe a schedule."""


def _ratio(factor: object) -> tuple[int, int]:
    """The factor as an exact (numerator, denominator) pair, never a float."""
    if isinstance(factor, (list, tuple)):
        num, den = factor
    else:
        num, den = factor, 1
    if den <= 0 or num < den:
        raise PolicyError(f"factor below 1: {factor!r}")
    return num, den


def plan(policy: dict, responses: list[Response], deadline_ms: int) -> list[Attempt]:
    """Return the attempts a client under `policy` would make against `responses`."""
    base_ms = policy["base_ms"]
    max_delay_ms = policy["max_delay_ms"]
    max_attempts = policy["max_attempts"]
    num, den = _ratio(policy["factor"])

    if base_ms <= 0:
        raise PolicyError(f"base_ms must be positive, got {base_ms!r}")
    if max_attempts < 1:
        raise PolicyError(f"max_attempts must be at least 1, got {max_attempts!r}")
    if deadline_ms < 0:
        raise PolicyError(f"deadline_ms must not be negative, got {deadline_ms!r}")

    out: list[Attempt] = []
    start = 0
    delay = 0

    # The record bounds the walk, so the loop can never run away.
    for number in range(1, min(max_attempts, len(responses)) + 1):
        if start >= deadline_ms:
            break

        out.append({"number": number, "start_ms": start, "delay_ms": delay})

        response = responses[number - 1]
        if response["status"] not in RETRYABLE:
            break  # 200, a listed terminal status, or anything unrecognised

        if "retry_after_ms" in response:
            delay = response["retry_after_ms"]  # deliberately not capped
        else:
            # Exact rational arithmetic, truncated once, then capped.
            exponent = number - 1  # the delay before attempt number + 1
            raw = base_ms * num**exponent // den**exponent
            delay = min(raw, max_delay_ms)
        start += delay

    return out
