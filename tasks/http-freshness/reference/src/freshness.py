"""Freshness of a stored HTTP response, an RFC 9111 subset. See task.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

FRESH = "FRESH"
STALE = "STALE"
MUST_REVALIDATE = "MUST_REVALIDATE"

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTH_NAMES = {
    name: i + 1
    for i, name in enumerate(
        "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    )
}
DIGITS = frozenset("0123456789")

REVALIDATING_DIRECTIVES = ("no-store", "no-cache", "must-revalidate")


class HeaderError(ValueError):
    """Raised for a header that is not a well-formed HTTP-date."""


@dataclass(frozen=True)
class Result:
    verdict: str
    current_age: int
    freshness_lifetime: int


def _header(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


def _digits(text: str, count: int | None = None) -> bool:
    if not text or (count is not None and len(text) != count):
        return False
    return all(ch in DIGITS for ch in text)


def _http_date(raw: str) -> int:
    """Parse an IMF-fixdate into epoch seconds, or raise HeaderError."""
    text = raw.strip()
    if len(text) != 29:
        raise HeaderError(f"not an HTTP-date: {raw!r}")
    if text[3:5] != ", " or text[7] != " " or text[11] != " " or text[16] != " ":
        raise HeaderError(f"not an HTTP-date: {raw!r}")
    if text[25:] != " GMT":
        raise HeaderError(f"not an HTTP-date: {raw!r}")
    if text[:3] not in DAY_NAMES or text[8:11] not in MONTH_NAMES:
        raise HeaderError(f"not an HTTP-date: {raw!r}")

    day, year, clock = text[5:7], text[12:16], text[17:25]
    if not _digits(day, 2) or not _digits(year, 4):
        raise HeaderError(f"not an HTTP-date: {raw!r}")
    if clock[2] != ":" or clock[5] != ":":
        raise HeaderError(f"not an HTTP-date: {raw!r}")
    hour, minute, second = clock[0:2], clock[3:5], clock[6:8]
    if not all(_digits(part, 2) for part in (hour, minute, second)):
        raise HeaderError(f"not an HTTP-date: {raw!r}")

    try:
        moment = datetime(
            int(year),
            MONTH_NAMES[text[8:11]],
            int(day),
            int(hour),
            int(minute),
            int(second),
            tzinfo=timezone.utc,
        )
    except ValueError as exc:
        raise HeaderError(f"not a real date: {raw!r}") from exc
    return int(moment.timestamp())


def _date_header(headers: dict[str, str], name: str) -> int | None:
    raw = _header(headers, name)
    return None if raw is None else _http_date(raw)


def _split_directives(value: str) -> list[str]:
    """Split on commas that are not inside a quoted string."""
    parts: list[str] = []
    buf: list[str] = []
    quoted = False
    for ch in value:  # bounded by len(value)
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
        elif ch == "," and not quoted:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [part.strip() for part in parts if part.strip()]


def _cache_control(headers: dict[str, str]) -> dict[str, str | None]:
    """Directive name -> value (None when written without one)."""
    raw = _header(headers, "cache-control")
    out: dict[str, str | None] = {}
    if raw is None:
        return out
    for item in _split_directives(raw):
        name, sep, value = item.partition("=")
        name = name.strip().lower()
        if not name:
            continue
        if not sep:
            out[name] = None
            continue
        value = value.strip()
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        out[name] = value
    return out


def _delta(directives: dict[str, str | None], name: str) -> int | None:
    """A directive's numeric value, or None when absent or unparseable."""
    if name not in directives:
        return None
    value = directives[name]
    if value is None or not _digits(value):
        return None
    return int(value)


def evaluate(
    response_headers: dict[str, str],
    request_headers: dict[str, str],
    request_time: int,
    response_time: int,
    now: int,
) -> Result:
    """Decide whether the stored response may be reused at `now`."""
    response_cc = _cache_control(response_headers)
    request_cc = _cache_control(request_headers)

    date = _date_header(response_headers, "date")
    if date is None:
        date = response_time
    expires = _date_header(response_headers, "expires")
    last_modified = _date_header(response_headers, "last-modified")

    raw_age = _header(response_headers, "age")
    age = int(raw_age.strip()) if raw_age is not None and _digits(raw_age.strip()) else 0

    # RFC 9111 §4.2.3
    apparent_age = max(0, response_time - date)
    corrected_age = age + (response_time - request_time)
    current_age = max(apparent_age, corrected_age) + (now - response_time)

    s_maxage = _delta(response_cc, "s-maxage")
    max_age = _delta(response_cc, "max-age")
    if s_maxage is not None:
        lifetime = s_maxage
    elif max_age is not None:
        lifetime = max_age
    elif expires is not None:
        lifetime = expires - date
    elif last_modified is not None:
        lifetime = (date - last_modified) // 10
    else:
        lifetime = 0
    lifetime = max(0, lifetime)

    request_max_age = _delta(request_cc, "max-age")
    if request_max_age is not None:
        lifetime = min(lifetime, request_max_age)

    verdict = _verdict(response_cc, request_cc, current_age, lifetime)
    return Result(verdict=verdict, current_age=current_age, freshness_lifetime=lifetime)


def _verdict(
    response_cc: dict[str, str | None],
    request_cc: dict[str, str | None],
    current_age: int,
    lifetime: int,
) -> str:
    if any(name in response_cc for name in REVALIDATING_DIRECTIVES):
        return MUST_REVALIDATE
    if "no-cache" in request_cc:
        return MUST_REVALIDATE

    min_fresh = _delta(request_cc, "min-fresh") or 0
    if lifetime > current_age + min_fresh:
        return FRESH

    if "max-stale" in request_cc:
        if request_cc["max-stale"] is None:
            return FRESH
        limit = _delta(request_cc, "max-stale")
        if limit is not None and current_age - lifetime <= limit:
            return FRESH
    return STALE
