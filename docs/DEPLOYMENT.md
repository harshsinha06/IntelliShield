# Deployment

This is the manual runbook. The repository does not deploy itself. Do not add a container file to follow these steps. The serving process is `uvicorn`. The dashboard is a Next.js build.

```text
User
  │
  ▼
Next.js on Vercel
  │  HTTPS
  ▼
FastAPI on a Python host
  ├── Random Forest bundle in ml/models/
  └── optional language-model API
```

History stays in SQLite on the API host. The browser never receives the language-model key.

## What the host must contain

Clone the repository. The API process imports `ml/src` and loads:

- `ml/models/phishing_rf.joblib`
- `ml/models/feature_config.json`
- `ml/models/metrics.json`

Those three files are part of the project. The training CSV is not required at request time. Leave `MODEL_PATH` empty unless you are deliberately pointing at that same bundle. `joblib` unpickles the file, so a different path is the same as running code from that file.

Start the API from `backend/`. `app.config` resolves the repository root from that layout, so `backend/` and `ml/` must stay siblings.

## API process

Python 3.13. From a checkout of the repository:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Use one process. SQLite is one file, and the request limit is an in-memory window in that process. Do not pass `--workers` greater than 1.

`--host 0.0.0.0` is required on a remote machine. The default bind address only accepts local connections.

A Python platform that runs this command directly is enough. On Render, choose the native Python web service, set the root to the repository, and use:

- Build: `pip install -r backend/requirements.txt`
- Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

That path does not use a Dockerfile. Any other host that can run the same command is fine. Put the public URL behind HTTPS. A Vercel page is HTTPS, and the browser will block a call to an `http://` API.

Health check path: `GET /health`. The status code is 200 when the process is up, including when `model_loaded` is false. The dashboard reads that flag. A check that only looks at the status code will not notice a missing model file.

## API environment

Set these on the Python host. Do not commit them. Names match `backend/.env.example`.

| Variable | Production value |
|----------|------------------|
| `CORS_ORIGINS` | The exact Vercel origin, for example `https://intellishield.vercel.app`. Add a preview origin only if that preview should be allowed. `*` is rejected at startup. |
| `OPENAI_API_KEY` | The language-model key, or empty. Empty keeps the classifier and sets `analysis.source` to `fallback`. The key stays on this host. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` when the key is set. |
| `OPENAI_MODEL` | The model name you choose. All three OpenAI values must be set or the explanation call is skipped. |
| `LLM_TIMEOUT_SECONDS` | `20` unless you have a reason to change it. |
| `DATABASE_URL` | `sqlite:////absolute/path/intellishield.db` on a disk that survives restarts. Empty uses `backend/data/intellishield.db`, which disappears on a host with an ephemeral filesystem. |
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_REQUESTS` | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` |
| `LOG_LEVEL` | `INFO` |
| `MODEL_PATH` | Empty. |
| `FEATURE_CONFIG_PATH` | Empty. |
| `METRICS_PATH` | Empty. |

The limit uses the address the process sees. It does not trust `X-Forwarded-For`. If the platform presents every visitor as the same proxy address, the 60 requests are shared. Raise the numbers in the environment if that happens, or put a limit on the proxy. Do not turn the limit off on a public URL.

## Dashboard on Vercel

In the Vercel project:

- Framework: Next.js
- Root directory: `frontend`
- Install, build, and start can stay on the defaults: `npm install`, `npm run build`, `npm run start`

Set this before the first production build. Next.js inlines it into the browser bundle:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | The API origin, with `https://` and no trailing slash. Example: `https://api.example.com` |

Do not create `NEXT_PUBLIC_OPENAI_API_KEY` or any other public secret. Changing `NEXT_PUBLIC_API_BASE_URL` later requires a new Vercel build.

After the API is reachable, set `CORS_ORIGINS` on the API to the Vercel origin and restart the API process. Order that works: deploy the API, copy its HTTPS URL into the Vercel variable, deploy the frontend, copy the Vercel origin into `CORS_ORIGINS`, restart the API.

## Check before you call it deployed

From your machine, against the public API:

```bash
curl -sS "https://YOUR_API/health"
curl -sS -X POST "https://YOUR_API/api/v1/predict" \
  -H "Content-Type: application/json" \
  -H "Origin: https://YOUR_VERCEL_APP" \
  -d '{"url":"https://www.uni-mainz.de"}'
```

`/health` should include `"model_loaded": true`. The predict response should include `"prediction": "safe"` for that URL. The response should include `access-control-allow-origin` set to the Vercel origin.

Then open the Vercel site and analyze `https://www.uni-mainz.de` and `http://192.0.2.10:8080/login`. The first is the known safe example. The second is the known phishing example. The status line should read “Analysis engine online”. A saved row should open from Recent analyses without scoring the URL again.

## Local production build

This does not publish anything. From `frontend/`, with the API already running on port 8000:

```bash
npm run build
npm run start
```

`npm run start` serves the production build on port 3000. `NEXT_PUBLIC_API_BASE_URL` still defaults to `http://localhost:8000` when the variable is unset.
