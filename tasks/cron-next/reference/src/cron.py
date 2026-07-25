"""Next firing times of a five-field cron expression. See task.md."""

from __future__ import annotations

from datetime import datetime, timedelta

MONTH_NAMES = {
    name: i + 1
    for i, name in enumerate(
        "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
    )
}
DOW_NAMES = {
    name: i for i, name in enumerate("SUN MON TUE WED THU FRI SAT".split())
}

SEARCH_YEARS = 5


class CronError(ValueError):
    """Raised for malformed expressions and for searches that find nothing."""


def _value(token: str, lo: int, hi: int, names: dict[str, int] | None) -> int:
    token = token.strip()
    if names and token.upper() in names:
        value = names[token.upper()]
    else:
        if not token.isdigit():
            raise CronError(f"not a value: {token!r}")
        value = int(token)
    if not lo <= value <= hi:
        raise CronError(f"{value} out of range {lo}-{hi}")
    return value


def _parse_term(
    term: str, lo: int, hi: int, names: dict[str, int] | None
) -> set[int]:
    body, sep, step_text = term.partition("/")
    if sep:
        if not step_text.isdigit() or int(step_text) < 1:
            raise CronError(f"bad step in {term!r}")
        step = int(step_text)
    else:
        step = 1

    body = body.strip()
    if body == "*":
        start, end = lo, hi
    elif "-" in body:
        head, _, tail = body.partition("-")
        start = _value(head, lo, hi, names)
        end = _value(tail, lo, hi, names)
        if start > end:
            raise CronError(f"range low above high: {term!r}")
    else:
        start = _value(body, lo, hi, names)
        end = hi if sep else start

    return set(range(start, end + 1, step))


def _parse_field(
    text: str, lo: int, hi: int, names: dict[str, int] | None
) -> set[int]:
    text = text.strip()
    if not text:
        raise CronError("empty field")
    values: set[int] = set()
    for term in text.split(","):
        if not term.strip():
            raise CronError(f"empty term in {text!r}")
        values |= _parse_term(term, lo, hi, names)
    return values


def _parse(expr: str) -> tuple[set[int], set[int], set[int], set[int], set[int], bool, bool]:
    fields = expr.split()
    if len(fields) != 5:
        raise CronError(f"expected 5 fields, got {len(fields)}")
    minute_text, hour_text, dom_text, month_text, dow_text = fields

    minutes = _parse_field(minute_text, 0, 59, None)
    hours = _parse_field(hour_text, 0, 23, None)
    doms = _parse_field(dom_text, 1, 31, None)
    months = _parse_field(month_text, 1, 12, MONTH_NAMES)
    dows = {d % 7 for d in _parse_field(dow_text, 0, 7, DOW_NAMES)}

    return (
        minutes,
        hours,
        doms,
        months,
        dows,
        dom_text.strip() != "*",
        dow_text.strip() != "*",
    )


def next_firings(expr: str, start: datetime, count: int) -> list[datetime]:
    """Return the next `count` firing times strictly after `start`."""
    minutes, hours, doms, months, dows, dom_restricted, dow_restricted = _parse(expr)

    if count < 0:
        raise CronError("count must not be negative")
    if count == 0:
        return []

    cursor = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = start + timedelta(days=366 * SEARCH_YEARS)

    sorted_hours = sorted(hours)
    sorted_minutes = sorted(minutes)

    out: list[datetime] = []
    day = cursor.date()

    while len(out) < count:
        if datetime.combine(day, datetime.min.time()) > limit:
            raise CronError("no firing found within five years")

        if day.month in months and _day_matches(
            day, doms, dows, dom_restricted, dow_restricted
        ):
            for hour in sorted_hours:
                for minute in sorted_minutes:
                    moment = datetime(day.year, day.month, day.day, hour, minute)
                    if moment >= cursor:
                        out.append(moment)
                        if len(out) == count:
                            return out
        day += timedelta(days=1)

    return out


def _day_matches(day, doms, dows, dom_restricted, dow_restricted) -> bool:
    cron_dow = (day.weekday() + 1) % 7
    if dom_restricted and dow_restricted:
        return day.day in doms or cron_dow in dows
    if dom_restricted:
        return day.day in doms
    if dow_restricted:
        return cron_dow in dows
    return True
