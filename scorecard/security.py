"""
Input validation and sanitization for URL/GET parameters to reduce injection and abuse risk.
"""
import re

# Senator IDs: alphanumeric, hyphen, underscore only; max length 50
SENATOR_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,50}$')

# County slug: lowercase letters, digits, hyphen; max 60
COUNTY_SLUG_PATTERN = re.compile(r'^[a-z0-9-]{1,60}$')

# Generic filter string: allow letters, digits, space, hyphen, underscore; max 200
FILTER_STRING_MAX_LENGTH = 200


def sanitize_senator_id(value: str) -> str | None:
    """Return value if it matches allowed senator_id format, else None."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    return s if SENATOR_ID_PATTERN.match(s) else None


def sanitize_senator_ids(value_list: list[str] | None, max_count: int = 5) -> list[str]:
    """Return list of valid senator_ids, capped at max_count. Drops invalid entries."""
    if not value_list:
        return []
    out = []
    for v in value_list[: max_count * 2]:  # allow some slack for split
        if isinstance(v, str):
            sid = sanitize_senator_id(v)
            if sid and sid not in out:
                out.append(sid)
                if len(out) >= max_count:
                    break
    return out[:max_count]


def sanitize_county_slug(value: str) -> str | None:
    """Return value if it matches allowed county slug format, else None."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip().lower()
    return s if COUNTY_SLUG_PATTERN.match(s) else None


def sanitize_filter_string(value: str) -> str:
    """Return a safe string for filter use: strip and limit length. No HTML."""
    if not value or not isinstance(value, str):
        return ""
    s = value.strip()
    if len(s) > FILTER_STRING_MAX_LENGTH:
        s = s[:FILTER_STRING_MAX_LENGTH]
    # Remove null bytes and control chars
    s = "".join(c for c in s if ord(c) >= 32 or c in "\t\n\r")
    return s


# Allowed engine types for HTMX partials (allowlist)
ALLOWED_ENGINE_TYPES = frozenset({"parliamentary"})


def sanitize_engine_type(value: str) -> str:
    """Return value if allowed, else 'unknown'."""
    if not value or not isinstance(value, str):
        return "unknown"
    v = value.strip().lower()
    return v if v in ALLOWED_ENGINE_TYPES else "unknown"
