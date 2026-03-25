"""
SENETRACK feedback form — spam & abuse protection.

Layers applied (in order):
  1.  Honeypot field    — bots fill the hidden field; humans don't
  2.  Timing check      — JS must have run and form must take ≥ 3 s to submit
  3.  Rate limiting     — DB-based per-IP and per-email caps
  4.  Duplicate check   — identical body from same IP within 24 h
  5.  Fake name         — test names, all-digits, keyboard mash
  6.  Non-Latin script  — blocks Cyrillic, CJK, Arabic, Hebrew, Thai, etc.
  7.  Gibberish         — vowel ratio, character variety, keyboard sequences
  8.  English abuse     — English-language profanity / insult patterns
  9.  Swahili abuse     — Swahili insult and obscene word list
  10. Spam signals      — URL flooding, excessive caps, char repetition
"""

import re
import time
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Rate-limit constants
# ─────────────────────────────────────────────────────────────────────────────

MIN_FORM_SECONDS    = 3   # seconds form must be open before submission
RATE_LIMIT_HOUR_MAX = 3   # max submissions per IP per hour
RATE_LIMIT_DAY_MAX  = 7   # max submissions per IP per 24 h
RATE_LIMIT_EMAIL_MAX = 2  # max submissions per email per 24 h

# ─────────────────────────────────────────────────────────────────────────────
# 2. Disposable email domains
# ─────────────────────────────────────────────────────────────────────────────

_DISPOSABLE_DOMAINS = frozenset([
    "mailinator.com", "guerrillamail.com", "trashmail.com", "tempmail.com",
    "10minutemail.com", "throwam.com", "yopmail.com", "sharklasers.com",
    "guerrillamailblock.com", "grr.la", "dispostable.com", "mailnull.com",
    "spam4.me", "trashmail.at", "trashmail.io", "wegwerfmail.de",
    "maildrop.cc", "fakeinbox.com", "spamgourmet.com", "spamhereplease.com",
    "mailnesia.com", "discard.email", "throwaway.email", "burnermail.io",
    "spamfree.email", "tempr.email", "emailondeck.com", "getairmail.com",
])

# ─────────────────────────────────────────────────────────────────────────────
# 3. Fake-name patterns
# ─────────────────────────────────────────────────────────────────────────────

_FAKE_NAME_EXACT = frozenset([
    "test", "admin", "user", "name", "foo", "bar", "baz",
    "john doe", "jane doe", "john smith", "jane smith",
    "test user", "anonymous", "anon", "nobody", "someone",
    "asdf", "qwerty", "aaaa", "haha", "lol", "xxx", "zzz",
])

# ─────────────────────────────────────────────────────────────────────────────
# 4. Non-Latin script detection
#
#    This platform is English-language only. Accented Latin characters
#    (é, ü, ñ, ā, etc.) are fine — they appear in African & international names.
#    Cyrillic, CJK, Arabic, Hebrew, Thai and other ideographic/syllabic scripts
#    are blocked entirely.
# ─────────────────────────────────────────────────────────────────────────────

# Regex matching any character from a blocked non-Latin Unicode block.
_NON_LATIN_RE = re.compile(
    "["
    "\u0400-\u04FF"   # Cyrillic (Russian, Ukrainian, Bulgarian …)
    "\u0500-\u052F"   # Cyrillic Supplement
    "\u2DE0-\u2DFF"   # Cyrillic Extended-A
    "\uA640-\uA69F"   # Cyrillic Extended-B
    "\u4E00-\u9FFF"   # CJK Unified Ideographs (Chinese / Japanese Kanji)
    "\u3400-\u4DBF"   # CJK Extension A
    "\uF900-\uFAFF"   # CJK Compatibility Ideographs
    "\u3040-\u309F"   # Hiragana (Japanese)
    "\u30A0-\u30FF"   # Katakana (Japanese)
    "\u31F0-\u31FF"   # Katakana Phonetic Extensions
    "\uAC00-\uD7AF"   # Hangul Syllables (Korean)
    "\u1100-\u11FF"   # Hangul Jamo
    "\uA960-\uA97F"   # Hangul Jamo Extended-A
    "\uD7B0-\uD7FF"   # Hangul Jamo Extended-B
    "\u0600-\u06FF"   # Arabic
    "\u0750-\u077F"   # Arabic Supplement
    "\u08A0-\u08FF"   # Arabic Extended-A
    "\uFB50-\uFDFF"   # Arabic Presentation Forms-A
    "\uFE70-\uFEFF"   # Arabic Presentation Forms-B
    "\u0590-\u05FF"   # Hebrew
    "\uFB00-\uFB4F"   # Alphabetic Presentation Forms (Hebrew)
    "\u0900-\u097F"   # Devanagari (Hindi, Sanskrit …)
    "\u0980-\u09FF"   # Bengali
    "\u0A00-\u0A7F"   # Gurmukhi (Punjabi)
    "\u0A80-\u0AFF"   # Gujarati
    "\u0B00-\u0B7F"   # Odia
    "\u0B80-\u0BFF"   # Tamil
    "\u0C00-\u0C7F"   # Telugu
    "\u0C80-\u0CFF"   # Kannada
    "\u0D00-\u0D7F"   # Malayalam
    "\u0E00-\u0E7F"   # Thai
    "\u0E80-\u0EFF"   # Lao
    "\u0F00-\u0FFF"   # Tibetan
    "\u1000-\u109F"   # Myanmar (Burmese)
    "\u10A0-\u10FF"   # Georgian
    "\u1200-\u137F"   # Ethiopic
    "\u13A0-\u13FF"   # Cherokee
    "\u1700-\u171F"   # Tagalog
    "]"
)

# Maximum non-Latin characters tolerated before rejecting.
# 0 for names (zero tolerance), 3 for body/subject (accidental paste buffer).
_MAX_NON_LATIN_NAME    = 0
_MAX_NON_LATIN_CONTENT = 2


def _non_latin_count(text: str) -> int:
    """Return the number of blocked non-Latin script characters in text."""
    return len(_NON_LATIN_RE.findall(text))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Gibberish detection
# ─────────────────────────────────────────────────────────────────────────────

_KEYBOARD_SEQS = [
    "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "qwerty", "asdfg", "zxcvb",
    "abcdef", "abcdefgh",
    "12345", "123456", "1234567890",
]
_REPEAT_RE = re.compile(r"(.)\1{5,}")   # same char repeated 6+ times in a row


def _is_gibberish(text: str, min_length: int = 15, threshold: float = 0.10) -> bool:
    """
    Return True if the text looks like keyboard mash / random characters.

    Heuristics:
      • Vowel-to-letter ratio below threshold (English prose ≈ 0.38)
      • Fewer than 5 unique Latin letters in a 15+ char string
      • Contains a known keyboard row sequence of ≥ 5 chars
      • A single character repeated 6+ consecutive times
    """
    letters = re.sub(r"[^a-zA-Z]", "", text).lower()
    if len(letters) < min_length:
        return False

    vowels = sum(1 for c in letters if c in "aeiou")
    if vowels / len(letters) < threshold:
        return True

    if len(set(letters)) < 5:
        return True

    lower = text.lower()
    for seq in _KEYBOARD_SEQS:
        if seq in lower:
            return True

    if _REPEAT_RE.search(text):
        return True

    return False

# ─────────────────────────────────────────────────────────────────────────────
# 6. English abuse / profanity patterns
#    Intentionally narrow — legitimate political language must not be blocked.
# ─────────────────────────────────────────────────────────────────────────────

_ENGLISH_ABUSE_RE = re.compile(
    r"\b("
    r"fuck(?:ing|er|s|ed|off|wit)?|"
    r"shit(?:ty|head|bag|s)?|"
    r"cunt|"
    r"bitch(?:es|ing)?|"
    r"ass(?:hole|wipe|face)s?|"
    r"motherfuck(?:er|ing)?|"
    r"dick(?:head|s)?|"
    r"pussy|"
    r"whore|"
    r"bastard(?:s)?|"
    r"retard(?:ed|s)?|"
    r"imbecile|"
    r"go (?:to )?hell|"
    r"kill your?self|"
    r"piece of (?:shit|crap)"
    r")\b",
    re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────────────────────
# 7. Swahili abuse / obscene word list
#    Words requested by the platform operator + common Swahili insults.
#    Variant spellings and common misspellings are covered where possible.
# ─────────────────────────────────────────────────────────────────────────────

_SWAHILI_ABUSE_RE = re.compile(
    r"\b("
    # Requested explicitly by operator
    r"umbwa|"                        # dog (insult)
    r"ma(?:k|c)ende|"               # vulgar: testicles
    r"mjinga|jinga|"                 # fool / idiot
    r"mwizi|wizi|"                   # thief
    # Common Swahili insults & obscenities
    r"punda|"                        # donkey (insult)
    r"fala|"                         # fool
    r"mshenzi|shenzi|"               # uncivilized / barbarian
    r"mavi|"                         # faeces / shit
    r"malaya|"                       # prostitute
    r"kichaa|"                       # madman / lunatic
    r"takataka|"                     # garbage / rubbish
    r"pumbavu|"                      # idiot / blockhead
    r"ng['\u2019]?ombe|"             # cow (used as insult; handle apostrophe variants)
    r"mwenda\s+wazimu|"              # lunatic
    r"mnyonge|"                      # weakling / worthless person
    r"mzigo|"                        # burden / nuisance
    r"bure\s+kabisa|"                # completely worthless
    r"chapaa|"                       # slang: broke / worthless
    r"fisadi|"                       # corrupt person (can be legitimate but often abusive)
    r"mnafiki|"                      # hypocrite (strong insult in context)
    r"mlaghai|laghai|"               # cheat / liar
    r"kabila\s+(?:yako|lako)\s+ni|"  # tribal hate speech opener
    r"nenda\s+(?:kaburi|jehanamu)|"  # "go to hell/grave" (death wish)
    r"nyamaza\s+(?:tuu?|kabisa)"     # "shut up" (aggressive form)
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Spam / flood signals
# ─────────────────────────────────────────────────────────────────────────────

_URL_RE      = re.compile(r"https?://|www\.", re.IGNORECASE)
_ALLCAPS_RE  = re.compile(r"[A-Z]{25,}")        # 25+ consecutive uppercase letters
_PUNCT_FLOOD = re.compile(r"[!?.,]{5,}")         # 5+ consecutive punctuation marks


def _has_english_abuse(text: str) -> bool:
    return bool(_ENGLISH_ABUSE_RE.search(text))


def _has_swahili_abuse(text: str) -> bool:
    return bool(_SWAHILI_ABUSE_RE.search(text))


def _has_spam_signals(text: str) -> bool:
    if len(_URL_RE.findall(text)) > 2:
        return True
    if _ALLCAPS_RE.search(text):
        return True
    if _PUNCT_FLOOD.search(text):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 9. SpamError (raised by flow-control checks; ValidationError for field checks)
# ─────────────────────────────────────────────────────────────────────────────

class SpamError(Exception):
    """Raised by flow-control guards (honeypot, timing, rate limit, duplicate)."""


# ─────────────────────────────────────────────────────────────────────────────
# 10. Public flow-control guards (called from the view)
# ─────────────────────────────────────────────────────────────────────────────

def check_honeypot(value: str) -> None:
    if value.strip():
        logger.warning("Honeypot triggered — blocking silently.")
        raise SpamError("honeypot")


def check_timing(loaded_at_ms_str: str) -> None:
    try:
        loaded_ms = float(loaded_at_ms_str)
    except (TypeError, ValueError):
        logger.warning("Timing field missing/invalid — possible bot.")
        raise SpamError("timing_missing")
    elapsed_s = (time.time() * 1000 - loaded_ms) / 1000
    if elapsed_s < MIN_FORM_SECONDS:
        logger.warning("Form submitted in %.1f s — too fast, blocking.", elapsed_s)
        raise SpamError("too_fast")


def check_rate_limit(ip: str | None, email: str) -> None:
    from scorecard.models import ContactMessage

    now = timezone.now()
    if ip:
        cutoff_hour = now - timedelta(hours=1)
        cutoff_day  = now - timedelta(hours=24)
        if ContactMessage.objects.filter(ip_address=ip, submitted_at__gte=cutoff_hour).count() >= RATE_LIMIT_HOUR_MAX:
            raise SpamError("rate_limit_hour")
        if ContactMessage.objects.filter(ip_address=ip, submitted_at__gte=cutoff_day).count() >= RATE_LIMIT_DAY_MAX:
            raise SpamError("rate_limit_day")

    if email:
        cutoff_day = now - timedelta(hours=24)
        if ContactMessage.objects.filter(email__iexact=email, submitted_at__gte=cutoff_day).count() >= RATE_LIMIT_EMAIL_MAX:
            raise SpamError("rate_limit_email")


def check_duplicate(ip: str | None, body: str) -> None:
    from scorecard.models import ContactMessage

    if not ip:
        return
    cutoff = timezone.now() - timedelta(hours=24)
    if ContactMessage.objects.filter(ip_address=ip, body=body.strip(), submitted_at__gte=cutoff).exists():
        raise SpamError("duplicate")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Public field-level validators (called from forms.py)
# ─────────────────────────────────────────────────────────────────────────────

_SCRIPT_ERROR_MSG = (
    "This platform only accepts messages written in English. "
    "Please rewrite your message using the Latin alphabet."
)

_ABUSE_ERROR_MSG = (
    "Your message contains language that is not appropriate for a civic platform. "
    "Please keep your feedback respectful and constructive."
)


def validate_name(value: str) -> None:
    """Validate name: length, fake patterns, non-Latin scripts, gibberish."""
    v = value.strip()

    if len(v) < 2:
        raise ValidationError("Please enter your real name.")

    if v.lower() in _FAKE_NAME_EXACT:
        raise ValidationError("Please enter your real name.")

    if re.fullmatch(r"[\d\s\W]+", v):
        raise ValidationError("Name must contain at least some letters.")

    if re.fullmatch(r"(.)\1+\s*", v):
        raise ValidationError("Please enter your real name.")

    if _non_latin_count(v) > _MAX_NON_LATIN_NAME:
        raise ValidationError(
            "Name must be written using the Latin alphabet (A–Z). "
            "Please use the English spelling of your name."
        )

    if _is_gibberish(v, min_length=4, threshold=0.05):
        raise ValidationError("That doesn't look like a real name. Please use your actual name.")


def validate_email_domain(value: str) -> None:
    """Block known disposable / throwaway email domains."""
    if not value:
        return
    domain = value.strip().lower().split("@")[-1]
    if domain in _DISPOSABLE_DOMAINS:
        raise ValidationError(
            "Please use a real email address. "
            "Disposable / throwaway addresses are not accepted."
        )


def validate_text_content(value: str, field_label: str = "This field") -> None:
    """
    Full content validation pipeline for subject and body fields.

    Order matters: script check first (clearest signal), then abuse,
    then spam, then gibberish.
    """
    v = value.strip()
    if not v:
        return  # let required= handle empty fields

    # ── Non-Latin script ──────────────────────────────────────────
    count = _non_latin_count(v)
    if count > _MAX_NON_LATIN_CONTENT:
        logger.info("Non-Latin script detected (%d chars) — blocking.", count)
        raise ValidationError(_SCRIPT_ERROR_MSG)

    # ── English abuse ─────────────────────────────────────────────
    if _has_english_abuse(v):
        raise ValidationError(_ABUSE_ERROR_MSG)

    # ── Swahili abuse ─────────────────────────────────────────────
    if _has_swahili_abuse(v):
        raise ValidationError(_ABUSE_ERROR_MSG)

    # ── Spam signals ──────────────────────────────────────────────
    if _has_spam_signals(v):
        raise ValidationError(
            f"{field_label} appears to contain spam content (e.g. multiple URLs, "
            "excessive repetition, or all-caps text). Please revise your message."
        )

    # ── Gibberish ─────────────────────────────────────────────────
    if _is_gibberish(v):
        raise ValidationError(
            f"{field_label} appears to be random characters or keyboard mashing. "
            "Please write a clear, meaningful message."
        )
