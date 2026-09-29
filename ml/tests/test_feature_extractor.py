"""Unit tests for lexical feature extraction."""

from src.feature_extractor import FEATURE_NAMES, extract_features


def test_feature_names_are_unique_and_at_least_twelve():
    assert len(FEATURE_NAMES) >= 12
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


def test_simple_https_url_features():
    url = "https://example.com/docs/guide"
    result = extract_features(url)
    assert result.error is None
    assert result.normalized_url == url
    assert list(result.features) == list(FEATURE_NAMES)
    assert result.features["url_length"] == 30
    assert result.features["hostname_length"] == len("example.com")
    assert result.features["domain_length"] == len("example.com")
    assert result.features["dot_count"] == 1
    assert result.features["subdomain_count"] == 0
    assert result.features["hyphen_count"] == 0
    assert result.features["special_char_count"] == 6
    assert result.features["digit_count"] == 0
    assert result.features["has_ip_address"] == 0
    assert result.features["uses_https"] == 1
    assert result.features["has_at_symbol"] == 0
    assert result.features["is_url_shortener"] == 0
    assert result.features["has_suspicious_keyword"] == 0
    assert result.features["path_segment_count"] == 2
    assert result.features["query_param_count"] == 0


def test_ip_port_query_and_keyword():
    url = "http://192.0.2.10:8080/login?next=a"
    result = extract_features(url)
    assert result.normalized_url == url
    assert result.features["url_length"] == 35
    assert result.features["hostname_length"] == 10
    assert result.features["domain_length"] == 10
    assert result.features["dot_count"] == 3
    assert result.features["subdomain_count"] == 0
    assert result.features["digit_count"] == 11
    assert result.features["has_ip_address"] == 1
    assert result.features["uses_https"] == 0
    assert result.features["has_suspicious_keyword"] == 1
    assert result.features["path_segment_count"] == 1
    assert result.features["query_param_count"] == 1
    assert result.features["special_char_count"] == 10


def test_keyword_match_is_whole_token_and_case_insensitive():
    assert extract_features("https://example.com/loginlogin").features["has_suspicious_keyword"] == 0
    assert extract_features("https://example.com/Login").features["has_suspicious_keyword"] == 1


def test_shortener_requires_a_label_boundary():
    assert extract_features("https://www.bit.ly/abc").features["is_url_shortener"] == 1
    assert extract_features("https://notbit.ly/abc").features["is_url_shortener"] == 0
    short = extract_features("https://www.bit.ly/abc")
    assert short.features["subdomain_count"] == 1
    assert short.features["domain_length"] == len("bit.ly")
    assert short.features["hostname_length"] == len("www.bit.ly")


def test_at_symbol_query_count_and_empty_path_segments():
    result = extract_features("http://user:secret@example.com/a//b/?x=1&y=&z=3")
    assert result.features["has_at_symbol"] == 1
    assert result.features["query_param_count"] == 3
    assert result.features["path_segment_count"] == 2


def test_fragment_is_removed_before_features_are_measured():
    result = extract_features("https://example.com/a#frag")
    assert result.normalized_url == "https://example.com/a"
    assert result.features["url_length"] == len("https://example.com/a")


def test_multipart_suffix_uses_the_last_two_labels():
    result = extract_features("https://www.voicefmradio.co.uk/listen")
    assert result.features["subdomain_count"] == 2
    assert result.features["domain_length"] == len("co.uk")
    assert result.features["hostname_length"] == len("www.voicefmradio.co.uk")


def test_ipv6_host_is_an_ip_address():
    result = extract_features("http://[2001:db8::1]/login")
    assert result.error is None
    assert result.features["has_ip_address"] == 1
    assert result.features["subdomain_count"] == 0
    assert result.normalized_url == "http://[2001:db8::1]/login"


def test_internationalized_hostname_is_punycode_in_the_normalized_url():
    result = extract_features("https://münchen.de/login")
    assert result.error is None
    assert result.normalized_url.startswith("https://xn--")
    assert result.features["has_suspicious_keyword"] == 1


def test_malformed_urls_return_errors_without_raising():
    cases = {
        "": "url_empty",
        "   ": "url_empty",
        "example.com": "scheme_must_be_http_or_https",
        "ftp://example.com/a": "scheme_must_be_http_or_https",
        "http://": "hostname_missing",
        "https://example .com": "url_has_whitespace_or_control_character",
    }
    for url, code in cases.items():
        result = extract_features(url)
        assert result.error == code
        assert result.features is None
    assert extract_features(None).error == "url_must_be_string"
    assert extract_features(123).error == "url_must_be_string"


def test_extraction_is_deterministic():
    url = "https://example.com/secure/update?id=7"
    assert extract_features(url) == extract_features(url)
