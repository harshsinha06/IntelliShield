# Testing

## What the suites cover

`backend/tests/` calls the FastAPI app with the saved forest. The shared client uses a temporary SQLite file and empty OpenAI settings, so a test does not write `backend/data/intellishield.db` and does not call a language model. Tests that need a reply inject a fake completion.

`backend/tests/test_security.py` checks the Phase 6 controls:

- `javascript:`, `data:`, `file:`, `ftp:`, an embedded space, and a missing host return `422` and the body does not echo the payload.
- `http://169.254.169.254/latest/meta-data` is scored without `urlopen` and without a chat request.
- A `$(whoami)` path stays a URL string.
- The access log for a predict call does not contain the URL token.
- A mocked chat reply that says `prediction: "safe"` does not change the forest label, and the URL text stays in the user message.
- The in-memory window blocks the third predict when the limit is 2, and `GET /health` still returns 200.
- `CORS_ORIGINS=*` is rejected when settings load.
- Frontend source, excluding `node_modules` and `.next`, contains no `dangerouslySetInnerHTML` and no `OPENAI_API_KEY`.

`ml/tests/` checks the extractor, the split, and `predict_url`. `ml/tests/test_metrics_record.py` reads `ml/models/metrics.json` and locks the saved overlap (all zeros), the test confusion counts (13 false positives, 86 false negatives), the test precision and recall, `class_weight: null`, and the cleaned class counts.

The dashboard has no separate test runner. `tsc --noEmit` and ESLint cover `app`, `components`, `hooks`, `lib`, and `types`.

## How to run

From `backend/`, with the project virtualenv:

```bash
/Users/harshsinha/Desktop/Resume_Projects/IntelliShield/ml/.venv/bin/python -m pytest --rootdir=. -q
```

From `ml/`:

```bash
/Users/harshsinha/Desktop/Resume_Projects/IntelliShield/ml/.venv/bin/python -m pytest --rootdir=. -q
```

From `frontend/`:

```bash
./node_modules/.bin/tsc --noEmit --pretty false
./node_modules/.bin/eslint app components hooks lib types
```

Dependency checks used for this pass:

```bash
python -m pip check
python -m pip_audit -r backend/requirements.txt -r ml/requirements.txt
npm audit
```

`pip-audit` was run as version 2.10.1 from a temporary directory. It is not a project dependency.

## Results of this pass

These are the commands after `pydantic-settings` was pinned to 2.14.2.

Backend, 28 September 2026:

```text
..............................................                           [100%]
46 passed, 1 warning in 2.97s
```

The warning is `StarletteDeprecationWarning`: `fastapi.testclient` still imports Starlette's `TestClient` from `httpx`, and that import asks for `httpx2`. The tests completed.

ML:

```text
....................                                                     [100%]
20 passed in 1.26s
```

Frontend:

```text
tsc --noEmit --pretty false    exit 0
eslint app components hooks lib types    exit 0
```

`pip check`:

```text
No broken requirements found.
```

`pip-audit` 2.10.1 against `backend/requirements.txt` and `ml/requirements.txt`, after the pin change:

```text
No known vulnerabilities found
```

The run before that pin reported one finding: `pydantic-settings` 2.14.0, CVE-2026-58203, fix version 2.14.2. The installed copy is now 2.14.2.

`npm audit` in `frontend/`:

```text
info 0, low 0, moderate 0, high 0, critical 0, total 0
dependencies total 439
exit 0
```
