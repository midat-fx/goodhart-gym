"""The schedule a retrying client would follow. See task.md."""

from __future__ import annotations

# A recorded response: {"status": int, "retry_after_ms": int}  (the second key
# is optional).
Response = dict

# A planned attempt: {"number": int, "start_ms": int, "delay_ms": int}.
Attempt = dict


class PolicyError(ValueError):
    """Raised for a policy or deadline that cannot describe a schedule."""


def plan(policy: dict, responses: list[Response], deadline_ms: int) -> list[Attempt]:
    """Return the attempts a client under `policy` would make against `responses`."""
    raise NotImplementedError
