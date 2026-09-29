"""Lexical URL features shared by training and predict_url.

Every feature is computed from the URL string. The extractor does not open
the network and does not read page content.

Feature spec: lexical-v1
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit, urlunsplit

FEATURE_SPEC_VERSION = "lexical-v1"
MAX_URL_LENGTH = 16384

FEATURE_NAMES: tuple[str, ...] = (
    "url_length",
    "hostname_length",
    "domain_length",
    "dot_count",
    "subdomain_count",
    "hyphen_count",
    "special_char_count",
    "digit_count",
    "has_ip_address",
    "uses_https",
    "has_at_symbol",
    "is_url_shortener",
    "has_suspicious_keyword",
    "path_segment_count",
    "query_param_count",
)

# Whole alphanumeric tokens. Matching is exact, so "loginlogin" does not
# count as "login". Brand names are omitted on purpose.
KEYWORD_LEXICON: tuple[str, ...] = (
    "login",
    "signin",
    "verify",
    "verification",
    "account",
    "secure",
    "security",
    "update",
    "confirm",
    "password",
    "banking",
    "wallet",
    "suspend",
    "suspended",
    "invoice",
    "credential",
    "unlock",
    "validate",
)

SHORTENERS: tuple[str, ...] = (
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
    "tiny.cc",
)

_KEYWORD_SET = frozenset(KEYWORD_LEXICON)
_SHORTENER_SET = frozenset(SHORTENERS)
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ExtractionResult:
    """A successful extract has features and a normalized URL.

    A failed extract has an error code and no feature dict. Callers must not
    treat a failure as a vector of zeros.
    """

    features: dict[str, int] | None
    normalized_url: str | None
    error: str | None

    @property
    def ok(self) -> bool:
        return self.error is None


def feature_config() -> dict:
    """Configuration persisted next to the model so inference cannot drift."""
    return {
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "keyword_lexicon": list(KEYWORD_LEXICON),
        "shorteners": list(SHORTENERS),
        "max_url_length": MAX_URL_LENGTH,
        "label_mapping": {"legitimate": 0, "phishing": 1},
        "source_label_mapping": {
            "phiusiil_0": "phishing",
            "phiusiil_1": "legitimate",
            "model_0": "legitimate",
            "model_1": "phishing",
        },
        "domain_length_rule": (
            "For a non-IP hostname with more than two labels, domain_length is "
            "the length of the last two labels joined by a dot. Otherwise it is "
            "the hostname length. This is not a Public Suffix List lookup."
        ),
        "subdomain_count_rule": (
            "max(label_count - 2, 0) for a non-IP hostname, else 0."
        ),
    }


def extract_features(url: object) -> ExtractionResult:
    """Normalize one URL and measure the lexical-v1 features.

    Malformed input returns an ExtractionResult with an error code.
    """
    if not isinstance(url, str):
        return _failure("url_must_be_string")

    raw = url.strip()
    if not raw:
        return _failure("url_empty")
    if len(raw) > MAX_URL_LENGTH:
        return _failure("url_too_long")
    if any(ord(char) < 32 or ord(char) == 127 or char.isspace() for char in raw):
        return _failure("url_has_whitespace_or_control_character")

    try:
        parts = urlsplit(raw)
    except ValueError:
        return _failure("url_unparseable")

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return _failure("scheme_must_be_http_or_https")

    hostname = parts.hostname
    if not hostname:
        return _failure("hostname_missing")
    hostname = hostname.rstrip(".").lower()
    if not hostname:
        return _failure("hostname_missing")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return _failure("hostname_idna_failed")

    is_ip = _is_ip_address(hostname)
    if is_ip is None:
        return _failure("hostname_invalid")

    userinfo = _userinfo(parts)
    host_for_netloc = f"[{hostname}]" if ":" in hostname else hostname
    netloc = host_for_netloc
    if parts.port is not None:
        netloc = f"{host_for_netloc}:{parts.port}"
    if userinfo:
        netloc = f"{userinfo}@{netloc}"

    normalized = urlunsplit((scheme, netloc, parts.path, parts.query, ""))
    domain_length, subdomain_count = _domain_and_subdomains(hostname, is_ip)
    tokens = _TOKEN_PATTERN.findall(normalized.lower())

    features = {
        "url_length": len(normalized),
        "hostname_length": len(hostname),
        "domain_length": domain_length,
        "dot_count": normalized.count("."),
        "subdomain_count": subdomain_count,
        "hyphen_count": normalized.count("-"),
        "special_char_count": _special_char_count(normalized),
        "digit_count": _digit_count(normalized),
        "has_ip_address": int(is_ip),
        "uses_https": int(scheme == "https"),
        "has_at_symbol": int("@" in normalized),
        "is_url_shortener": _is_shortener(hostname),
        "has_suspicious_keyword": int(any(token in _KEYWORD_SET for token in tokens)),
        "path_segment_count": sum(1 for segment in parts.path.split("/") if segment),
        "query_param_count": len(parse_qsl(parts.query, keep_blank_values=True)),
    }
    missing = [name for name in FEATURE_NAMES if name not in features]
    if missing:
        return _failure("feature_spec_incomplete")
    ordered = {name: int(features[name]) for name in FEATURE_NAMES}
    return ExtractionResult(features=ordered, normalized_url=normalized, error=None)


def _failure(code: str) -> ExtractionResult:
    return ExtractionResult(features=None, normalized_url=None, error=code)


def _is_ip_address(hostname: str) -> bool | None:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if " " in hostname or "/" in hostname:
            return None
        return False
    return True


def _userinfo(parts) -> str | None:
    if parts.username is None:
        return None
    if parts.password is None:
        return parts.username
    return f"{parts.username}:{parts.password}"


def _domain_and_subdomains(hostname: str, is_ip: bool) -> tuple[int, int]:
    if is_ip:
        return len(hostname), 0
    labels = [label for label in hostname.split(".") if label]
    if len(labels) <= 2:
        return len(hostname), 0
    domain = ".".join(labels[-2:])
    return len(domain), len(labels) - 2


def _is_shortener(hostname: str) -> int:
    if hostname in _SHORTENER_SET:
        return 1
    return int(any(hostname.endswith("." + name) for name in _SHORTENER_SET))


def _special_char_count(text: str) -> int:
    return sum(
        1
        for char in text
        if not ("a" <= char <= "z" or "A" <= char <= "Z" or "0" <= char <= "9")
    )


def _digit_count(text: str) -> int:
    return sum(1 for char in text if "0" <= char <= "9")
