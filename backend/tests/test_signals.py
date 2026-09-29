"""Signal selection uses saved importances and does not rescore the URL."""

from app.services.feature_service import build_signals


def test_active_http_indicator_is_included_and_ordered_by_importance() -> None:
    features = {
        "url_length": 40,
        "hostname_length": 11,
        "domain_length": 11,
        "dot_count": 1,
        "subdomain_count": 0,
        "hyphen_count": 0,
        "special_char_count": 8,
        "digit_count": 0,
        "has_ip_address": 1,
        "uses_https": 0,
        "has_at_symbol": 0,
        "is_url_shortener": 0,
        "has_suspicious_keyword": 1,
        "path_segment_count": 1,
        "query_param_count": 0,
    }
    importances = {name: 0.01 for name in features}
    importances["uses_https"] = 0.5
    importances["has_ip_address"] = 0.02
    importances["has_suspicious_keyword"] = 0.03
    signals = build_signals(features, importances)
    names = [signal.feature for signal in signals]
    assert "uses_https" in names
    assert "has_ip_address" in names
    assert "has_suspicious_keyword" in names
    assert names == sorted(names, key=lambda name: importances[name], reverse=True)
    assert len(signals) == 5
    http_signal = next(signal for signal in signals if signal.feature == "uses_https")
    assert http_signal.summary == "The URL uses HTTP."
