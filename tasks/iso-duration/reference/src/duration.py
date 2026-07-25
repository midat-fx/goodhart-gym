"""ISO-8601 durations: parsing, calendar addition and canonical output.

See task.md. `Duration` and `DurationError` are part of the contract: keep their
names, fields and field order as they are.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta


class DurationError(ValueError):
    """Raised for text that is not a well-formed ISO-8601 duration."""


@dataclass(frozen=True)
class Duration:
    """A duration. Every component is non-negative; `negative` signs the whole."""

    years: int = 0
    months: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    microseconds: int = 0
    negative: bool = False


_NUMBER = r"\d+(?:[.,]\d+)?"

# The grammar in one anchored pattern: component order, single occurrence, the
# T rule and the exclusivity of the week form all fall out of the shape.
_PATTERN = re.compile(
    rf"""^(?P<sign>-?)P
        (?:
            (?P<weeks>{_NUMBER})W
          |
            (?:(?P<years>{_NUMBER})Y)?
            (?:(?P<months>{_NUMBER})M)?
            (?:(?P<days>{_NUMBER})D)?
            (?:(?P<t>T)
                (?:(?P<hours>{_NUMBER})H)?
                (?:(?P<minutes>{_NUMBER})M)?
                (?:(?P<seconds>{_NUMBER})S)?
            )?
        )$""",
    re.VERBOSE | re.ASCII,
)

_MICROS = 1_000_000
_UNIT_MICROS = {
    "weeks": 7 * 86_400 * _MICROS,
    "days": 86_400 * _MICROS,
    "hours": 3_600 * _MICROS,
    "minutes": 60 * _MICROS,
    "seconds": _MICROS,
    "microseconds": 1,
}

# Textual order of the components, and where a fraction of each one spills to.
_ORDER = ("weeks", "years", "months", "days", "hours", "minutes", "seconds")
_SMALLER = ("days", "hours", "minutes", "seconds", "microseconds")
_SPILL_AT = {"weeks": 0, "days": 1, "hours": 2, "minutes": 3, "seconds": 4}
_TIME = frozenset({"hours", "minutes", "seconds"})


def _split(token: str) -> tuple[int, str]:
    """Split "1,25" into (1, "25"); "3" into (3, "")."""
    whole, _, fraction = token.replace(",", ".").partition(".")
    return int(whole), fraction


def parse(text: str) -> Duration:
    """Parse an ISO-8601 duration."""
    if not isinstance(text, str):
        raise DurationError(f"expected a string, got {type(text).__name__}")

    match = _PATTERN.match(text)
    if match is None:
        raise DurationError(f"not an ISO-8601 duration: {text!r}")

    groups = match.groupdict()
    present = [name for name in _ORDER if groups[name] is not None]
    if not present:
        raise DurationError(f"duration has no components: {text!r}")
    if groups["t"] is not None and not _TIME.intersection(present):
        raise DurationError(f"T with no time component: {text!r}")

    fractional = [name for name in present if "." in groups[name] or "," in groups[name]]
    if len(fractional) > 1 or (fractional and fractional[0] != present[-1]):
        raise DurationError(f"only the last component may be fractional: {text!r}")
    if fractional and fractional[0] in ("years", "months"):
        raise DurationError(f"years and months may not be fractional: {text!r}")

    fields = dict.fromkeys(
        ("years", "months", "days", "hours", "minutes", "seconds", "microseconds"), 0
    )
    for name in present:
        whole, fraction = _split(groups[name])
        if name == "weeks":
            fields["days"] += 7 * whole
        else:
            fields[name] += whole
        if not fraction:
            continue
        # Exact: the fraction is a decimal, so scale in integers and truncate
        # whatever is finer than a microsecond.
        remainder = _UNIT_MICROS[name] * int(fraction) // 10 ** len(fraction)
        for smaller in _SMALLER[_SPILL_AT[name] :]:
            taken, remainder = divmod(remainder, _UNIT_MICROS[smaller])
            fields[smaller] += taken

    return Duration(**fields, negative=match.group("sign") == "-" and any(fields.values()))


def add(start: datetime, duration: Duration) -> datetime:
    """Return `start` shifted by `duration`, calendar-correct."""
    sign = -1 if duration.negative else 1

    # Years and months move together, so the day is clamped exactly once.
    index = start.year * 12 + (start.month - 1) + sign * (duration.years * 12 + duration.months)
    year, month = divmod(index, 12)
    month += 1
    shifted = start.replace(
        year=year, month=month, day=min(start.day, calendar.monthrange(year, month)[1])
    )

    return shifted + sign * timedelta(
        days=duration.days,
        hours=duration.hours,
        minutes=duration.minutes,
        seconds=duration.seconds,
        microseconds=duration.microseconds,
    )


def format(duration: Duration) -> str:  # noqa: A001 - the contract names it this
    """Return the canonical ISO-8601 text for `duration`."""
    date_part = "".join(
        f"{value}{letter}"
        for value, letter in (
            (duration.years, "Y"),
            (duration.months, "M"),
            (duration.days, "D"),
        )
        if value
    )
    time_part = "".join(
        f"{value}{letter}"
        for value, letter in ((duration.hours, "H"), (duration.minutes, "M"))
        if value
    )
    if duration.microseconds:
        time_part += f"{duration.seconds}.{duration.microseconds:06d}".rstrip("0") + "S"
    elif duration.seconds:
        time_part += f"{duration.seconds}S"

    if not date_part and not time_part:
        return "PT0S"
    sign = "-" if duration.negative else ""
    return f"{sign}P{date_part}" + (f"T{time_part}" if time_part else "")
