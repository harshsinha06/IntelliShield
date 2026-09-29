# IntelliShield — Feature Engineering

Spec version: `lexical-v1`

Training and `predict_url` both call `extract_features` in `ml/src/feature_extractor.py`. The function returns 15 integers in the order below, or an error code and no vector. A failed URL is dropped during training. It is not filled with zeros.

The formulas use the Python standard library: `urllib.parse`, `ipaddress`, and `re`.

## What this spec replaced

The design draft used 16 features, including Shannon entropy, punycode, and a non-standard port flag. Phase 1 uses the 15 measurements below so the implemented set matches the requested URL properties: lengths, dots, subdomains, hyphens, special characters, digits, IP host, HTTPS, `@`, shorteners, suspicious keywords, path segments, query parameters, and domain length.

## Normalization

Applied before any count:

1. Strip the string. Reject a non-string, an empty string, a string longer than 16,384 characters, and any string that contains whitespace or an ASCII control character.
2. Parse with `urlsplit`. The scheme must be `http` or `https` after lowercasing. A missing scheme is an error. The extractor does not invent `https://`.
3. Require a hostname. Lowercase it, strip one trailing dot, and encode it with IDNA. A hostname that cannot be encoded is an error.
4. Keep an explicit port and userinfo. Drop the fragment. Keep the path and query as parsed.
5. Rebuild the URL. Features that read the whole string use this rebuilt URL. An IPv6 host is written with brackets.

Malformed input returns one of: `url_must_be_string`, `url_empty`, `url_too_long`, `url_has_whitespace_or_control_character`, `url_unparseable`, `scheme_must_be_http_or_https`, `hostname_missing`, `hostname_idna_failed`, `hostname_invalid`.

## Canonical order

This order is `FEATURE_NAMES` and the `feature_names` array in `ml/models/feature_config.json`. The forest was fit on a dataframe with these columns, and `predict_url` builds its row in the same order. If the code and the JSON disagree, prediction stops.

| # | Name | Type |
|---|------|------|
| 1 | `url_length` | int |
| 2 | `hostname_length` | int |
| 3 | `domain_length` | int |
| 4 | `dot_count` | int |
| 5 | `subdomain_count` | int |
| 6 | `hyphen_count` | int |
| 7 | `special_char_count` | int |
| 8 | `digit_count` | int |
| 9 | `has_ip_address` | 0 or 1 |
| 10 | `uses_https` | 0 or 1 |
| 11 | `has_at_symbol` | 0 or 1 |
| 12 | `is_url_shortener` | 0 or 1 |
| 13 | `has_suspicious_keyword` | 0 or 1 |
| 14 | `path_segment_count` | int |
| 15 | `query_param_count` | int |

## Definitions

### `url_length`

`len(normalized_url)`.

### `hostname_length`

`len(hostname)` after IDNA and lowercasing. Brackets around an IPv6 address are not included.

### `domain_length`

For an IP hostname, this is `hostname_length`.

For any other hostname, split on `.` and drop empty labels. If there are two or fewer labels, `domain_length` is `hostname_length`. If there are more, it is the length of the last two labels joined by a dot. `www.example.com` has domain length `len("example.com")`. `www.voicefmradio.co.uk` has domain length `len("co.uk")`, because this rule is not a Public Suffix List lookup. The limitation is locked by a unit test.

### `dot_count`

Number of `.` characters in the normalized URL, including the host, path, and query.

### `subdomain_count`

`0` when the host is an IP address. Otherwise `max(label_count - 2, 0)` using the same labels as `domain_length`. `www.example.com` is 1. `example.com` is 0. The `.co.uk` case is counted as two labels of "domain," so `www.example.co.uk` is 2 rather than 1.

### `hyphen_count`

Number of `-` characters in the normalized URL. This includes the path and the query, not only the hostname.

### `special_char_count`

Number of characters in the normalized URL that are not ASCII letters or ASCII digits. Dots, slashes, colons, and question marks all count. The count moves with URL structure, so it is correlated with length. The forest can still split on it.

### `digit_count`

Number of ASCII digits in the normalized URL.

### `has_ip_address`

`1` when `ipaddress.ip_address` accepts the hostname. Covers IPv4 and IPv6.

### `uses_https`

`1` when the scheme is `https`. This records the scheme written in the URL. It does not check a certificate.

On the PhiUSIIL file used for training, every legitimate URL is HTTPS and every HTTP URL is phishing. That measured composition is in `ML_PIPELINE.md`. It is why this feature has the largest importance in the saved forest. HTTPS is not evidence that a site is trustworthy.

### `has_at_symbol`

`1` when `@` appears anywhere in the normalized URL, including userinfo.

### `is_url_shortener`

`1` when the hostname equals one of the hosts below, or ends with `.<host>`. `www.bit.ly` matches. `notbit.ly` does not.

```text
bit.ly, tinyurl.com, t.co, goo.gl, ow.ly, is.gd,
buff.ly, cutt.ly, rb.gy, shorturl.at, tiny.cc
```

The list is frozen in `feature_config.json` with the model. A shortener hides the destination. It is not, by itself, a phishing label.

### `has_suspicious_keyword`

`1` when any alphanumeric token of the lowercased normalized URL is in this list:

```text
login, signin, verify, verification, account, secure, security,
update, confirm, password, banking, wallet, suspend, suspended,
invoice, credential, unlock, validate
```

Tokens are runs of ASCII letters and digits. `login` matches. `loginlogin` does not. `Login` matches because the check lowercases the URL. Brand names are not in the list.

### `path_segment_count`

Number of non-empty segments in `path.split("/")`. `/a//b/` is 2.

### `query_param_count`

`len(parse_qsl(query, keep_blank_values=True))`. An empty query is 0.

## Worked example

`https://example.com/docs/guide` is unchanged by normalization.

| Feature | Value |
|---------|------:|
| url_length | 30 |
| hostname_length | 11 |
| domain_length | 11 |
| dot_count | 1 |
| subdomain_count | 0 |
| hyphen_count | 0 |
| special_char_count | 6 |
| digit_count | 0 |
| has_ip_address | 0 |
| uses_https | 1 |
| has_at_symbol | 0 |
| is_url_shortener | 0 |
| has_suspicious_keyword | 0 |
| path_segment_count | 2 |
| query_param_count | 0 |

`http://192.0.2.10:8080/login?next=a`: IP host, so `subdomain_count` is 0 and `domain_length` equals `hostname_length` (10). `digit_count` is 11. `has_ip_address` is 1. `has_suspicious_keyword` is 1 because of the token `login`. `query_param_count` is 1. `special_char_count` is 10.

## Importance in the trained forest

From the saved model in this experiment. The full metric record is in `ML_PIPELINE.md`.

| Feature | Importance |
|---------|-----------:|
| uses_https | 0.398236 |
| special_char_count | 0.140812 |
| digit_count | 0.118203 |
| url_length | 0.090000 |
| path_segment_count | 0.051152 |
| domain_length | 0.049926 |
| subdomain_count | 0.039821 |
| dot_count | 0.037616 |
| hostname_length | 0.035622 |
| hyphen_count | 0.035088 |
| query_param_count | 0.001637 |
| has_suspicious_keyword | 0.001611 |
| is_url_shortener | 0.000179 |
| has_at_symbol | 0.000091 |
| has_ip_address | 0.000006 |

`uses_https` ranks first because of the corpus composition documented in the pipeline note, not because the extractor treats HTTPS as proof of safety. `has_ip_address`, `has_at_symbol`, and `is_url_shortener` are near zero on this file because those patterns are rare in it. The features stay in the vector so inference and training still share one definition.

## Tests

`ml/tests/test_feature_extractor.py` locks the worked values, whole-token keyword matching, the shortener boundary, IPv6, fragment stripping, the `.co.uk` label rule, and malformed inputs. `ml/tests/test_preprocessing.py` checks the PhiUSIIL label direction, that the loader does not keep the extra columns, and that normalized URLs do not cross the train, validation, and test partitions.
