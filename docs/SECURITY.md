# Security

This pass records what the current code does. It is a local portfolio service, not a hardened public deployment.

## Backend

### Input validation

`POST /api/v1/predict` accepts one JSON field, `url`. Pydantic strips surrounding whitespace and rejects a blank string. The extractor then rejects a string longer than 16384 characters, whitespace or control characters inside the string, a missing or unparseable host, an IDNA failure, and any scheme other than `http` or `https`. A rejected URL returns `422` with `validation_error`. The message is a fixed sentence. The body does not repeat the submitted string.

Extra JSON fields, including a `model_path`, are ignored. The model file is chosen by `MODEL_PATH`, not by the request.

### Malformed URLs

`javascript:`, `data:`, and `file:` fail the scheme check. A URL with an embedded space fails the whitespace check. `http://` with no host fails the hostname check. Schemeless text is not rewritten to `https`.

### SSRF

The predict route does not open a socket to the submitted host. Normalization and feature extraction are string operations. `http://169.254.169.254/...` is scored as text.

The only optional outbound HTTP call is `POST {OPENAI_BASE_URL}/chat/completions`, and only when the API key, base URL, and model name are all set. That host comes from the operator environment, not from the submitted URL. The training downloader uses `urllib.request.urlopen` for the PhiUSIIL CSV. That code is not on the request path.

### Command injection

The URL is never passed to a shell. Characters such as `$(whoami)` stay inside the string that the extractor counts.

### Prompt injection

A URL can contain text that tries to instruct the language model. The system prompt tells the model that the URL is untrusted data, that `classifier_prediction` is already final, and that the reply must be one JSON object with `summary`, `reasoning`, `risk_factors`, and `recommendations`. Extra keys, including a label, are dropped. `prediction`, `probability`, and `risk_level` are set from the forest before `explain()` runs and are not read back from the reply. A timeout, HTTP error, or invalid JSON replaces the narrative with fallback text built from the label and the signal sentences.

This limits what a malicious URL can change. It does not make prompt injection impossible. The summary is still model-generated text and can be wrong. The dashboard shows that text as an explanation of the forest label.

### API error handling

| Status | Code | Client sees |
|--------|------|-------------|
| 422 | `validation_error` | A fixed validation sentence. The input is not echoed. |
| 429 | `rate_limited` | `Too many requests. Try again shortly.` plus `Retry-After`. |
| 404 | `not_found` | `That analysis was not found.` |
| 503 | `model_unavailable` | `The detection model is not loaded.` The filesystem path is not included. |
| 500 | `internal_error` | `The analysis could not be completed.` |

An unexpected exception is logged as its type name. The response does not include the exception text, because that text can contain the URL.

### Rate limiting

`POST /api/v1/predict` and `GET /api/v1/history` share an in-memory sliding window. The default is 60 requests per 60 seconds. The key is the direct client address. `X-Forwarded-For` is not trusted, because the caller can set it. `OPTIONS` and `GET /health` are not counted. `RATE_LIMIT_ENABLED=false` turns the window off.

The counter lives in the process. It resets on restart and is not shared across workers. A reverse proxy in front of this API still needs its own limit.

### CORS

`CORS_ORIGINS` is a comma-separated list. The default is `http://localhost:3000`. A value of `*` is rejected when settings load, so the process does not start with a wildcard origin. Credentials are not allowed. Allowed methods are `GET`, `POST`, and `OPTIONS`. The allowed request header is `Content-Type`.

### Secrets

`OPENAI_API_KEY` is a `SecretStr`. It is read only in the FastAPI process and sent as a bearer token to the configured chat endpoint. It is not written to history, not returned by the API, and not placed in a `NEXT_PUBLIC_` variable.

Before a row is stored, and before facts are sent to the language model, userinfo is replaced with `REDACTED` and each query value is replaced with `REDACTED`. Query names, the host, the port, and the path are kept. A secret that appears only in the path is still stored. The immediate predict response still returns the normalized URL to the person who submitted it, including userinfo and query values.

### Logging

Access lines contain the request id, method, path, and status. Prediction lines contain the label and risk level. History lines contain the row id and the label. Explanation lines contain `source=llm` or `source=fallback` and a reason code. These lines do not include the URL, the query string, userinfo, the prompt, or the API key.

SQLAlchemy engine logging is set to warning so SQL parameters are not written at info. Unexpected errors and history-save failures are logged as the exception type, not as a traceback, because a traceback message can contain the URL.

### Dependency security

Python dependencies in `backend/requirements.txt` and `ml/requirements.txt` are pinned to exact versions.

`pip-audit` 2.10.1, run against both files, first reported `pydantic-settings` 2.14.0 as CVE-2026-58203, fixed in 2.14.2. That issue is a symlink read in `NestedSecretsSettingsSource` when `secrets_nested_subdir` is on. This service does not use that source or a secrets directory. The pin was still raised to 2.14.2. The same command after the bump reported no known vulnerabilities. `pip check` reported no broken requirements.

`npm audit` in `frontend/` reported 0 vulnerabilities across 439 dependencies. The command output is in `TESTING.md`.

### Model loading

`joblib.load` unpickles the bundle. Unpickling can execute code. `MODEL_PATH` is an operator trust boundary, equivalent to running code from that file. The path is never taken from the request, and the API does not accept an uploaded model. After load, the forest classes must be `{0, 1}` and the feature names, lexicon, shortener list, and spec version must match the extractor. A mismatch returns `503` without the path.

## Frontend

### XSS

Dashboard components render the URL, the explanation, and the signal sentences as React text. There is no `dangerouslySetInnerHTML` in the application source. React escapes those strings. The submitted URL is not turned into a link.

### Input sanitization

The browser sends the typed string as JSON. It does not rewrite the URL before the request. Changing the string in the browser would score a different URL than the one the user typed. The API is the validator.

### API error handling

A non-OK response shows `error.message` from the JSON body. A network failure shows a connection error. The form does not invent a prediction when the request fails. A `429` is shown with the same error text as any other API error.

### Environment variables

The only public variable is `NEXT_PUBLIC_API_BASE_URL`. The default is `http://localhost:8000`. `.env*` is gitignored, with `.env.example` kept. An API key must not be given a `NEXT_PUBLIC_` name. Next.js inlines `NEXT_PUBLIC_` values into the browser bundle.

## Residual risk

- The in-memory limit does not protect a multi-worker or proxied deployment by itself.
- Path secrets are stored.
- The language-model summary can still be misleading.
- Anyone who can set `MODEL_PATH` can execute code through the pickle.
- The holdout scores do not measure live false positives. See `MODEL_LIMITATIONS.md`.
