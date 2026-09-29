# IntelliShield — Project Overview

IntelliShield is a phishing-detection web application. A person pastes a URL. The system validates it, measures a fixed set of lexical features, scores it with a trained Random Forest, and asks an LLM to explain that score in plain language. The browser shows the verdict, the probability, the signals, and the explanation on one dashboard.

Phase 1 is implemented in `ml/`. The training set, the 15 lexical features, and the measured scores are in `ML_PIPELINE.md` and `FEATURE_ENGINEERING.md`. The FastAPI service is in `backend/`. The dashboard is in `frontend/`.

## Problem

Phishing pages impersonate legitimate sites and hide behind ordinary-looking links. A portfolio project that only calls an LLM to "decide if a URL is bad" cannot show a real machine-learning pipeline, and a model that only returns a label is hard to trust. IntelliShield separates those jobs:

- A classical classifier produces the verdict and the probability.
- Feature signals show which measurements pushed that verdict.
- An LLM explains the classifier's output. It does not replace the classifier.

## Users

One user, in a browser, checking one URL at a time. There is no account system in the first version.

## What the product does

1. Accept a URL from the Next.js form.
2. Validate and normalize it in FastAPI.
3. Extract the 15 lexical features in `FEATURE_ENGINEERING.md` from the normalized URL.
4. Run a persisted scikit-learn Random Forest.
5. Return `phishing` or `legitimate`, plus the phishing probability.
6. Rank the features that point toward the predicted class.
7. Send the verdict, probability, and those signals to an OpenAI-compatible chat API.
8. Render a cybersecurity-style result view.

The model never fetches the page. Inference uses the URL string only. That keeps training and serving on the same inputs, and it avoids turning the API into an open proxy that requests arbitrary hosts.

## Architecture in one page

```text
Browser (Next.js)
    │  POST /api/v1/analyze
    ▼
FastAPI
    ├── URL validation and normalization
    ├── Lexical feature extraction          (same function used in training)
    ├── Random Forest inference             (joblib bundle on disk)
    ├── Threat-signal ranking               (training medians + global importance)
    └── LLM explanation                     (OpenAI-compatible API, with template fallback)
    ▼
JSON response
    ▼
Next.js result dashboard
```

There is no database. The trained model bundle is a file. Submitted URLs are not stored.

## Repository layout

```text
IntelliShield/
├── docs/
│   ├── PROJECT_OVERVIEW.md       this file
│   ├── WORKFLOW.md               request path from browser to dashboard
│   ├── HLD.md                    high-level design
│   ├── API_SPECIFICATION.md      HTTP contracts
│   ├── ML_PIPELINE.md            data, training, inference, explanation
│   └── FEATURE_ENGINEERING.md    the 15 features and how each is computed
├── ml/                           Phase 1 training package
│   ├── data/                     PhiUSIIL CSV (gitignored)
│   ├── notebooks/
│   ├── src/                      loader, features, split, train, evaluate, predict
│   ├── tests/
│   ├── models/                   joblib bundle, feature_config.json, metrics.json
│   └── requirements.txt
├── backend/                      FastAPI service
└── frontend/                     Next.js dashboard
```

`ml/src/feature_extractor.py` is the feature function for training and for `predict_url`. The later API should import that module rather than reimplement the formulas.

## Decisions

Each decision below is a constraint on later phases. Changing one means updating the docs that depend on it.

| # | Decision | Why |
|---|----------|-----|
| D1 | Train on raw URLs from the PhiUSIIL dataset (Prasad & Chandra), then compute our own features. | The file has 235,795 URLs and a label, which meets the phase-1 size requirement. License CC BY 4.0. Measured counts and scores are in `ML_PIPELINE.md`. |
| D2 | Use the 15 lexical features defined in `FEATURE_ENGINEERING.md`. | Every feature can be recomputed from a URL string with the Python standard library. |
| D3 | Leave PhiUSIIL's published numeric feature columns unused. | Many of them come from page HTML or from statistics derived on the corpus. `predict_url` cannot recompute them from a URL string. |
| D4 | Classifier is scikit-learn `RandomForestClassifier`, saved with joblib. | It matches the requested stack, handles mixed binary and numeric features without scaling, and exposes global feature importances. |
| D5 | Positive class is phishing. API field `phishing_probability` is `P(status = phishing)`. | The product question is "how phishing-like is this URL?" |
| D6 | The LLM receives the verdict and signals and writes `analysis`. A failed or unconfigured call returns fallback text with the same JSON shape. | The classifier decision stays available when the language API is down. |
| D7 | History is a local SQLite file. Query values and userinfo are removed before insert. Request logs still omit the URL. | The dashboard can reopen a score without keeping tokens that arrived in the query string. |
| D8 | Do not fetch, resolve, or follow the submitted URL. | Fetching user-supplied URLs from the server is server-side request forgery. Many phishing pages are also already offline, so a live fetch would make training and serving disagree. |
| D9 | Reported accuracy, F1, and similar scores are produced by `ml/train.py` and written next to the model file. | This design does not invent model metrics. The papers' published scores are not IntelliShield's scores. |
| D10 | API signals are the active indicators plus the highest-importance features, ordered by the importances in `metrics.json`. | Class medians were not saved with the forest. The sentences describe the measured value. They are not a second classifier. |

## Build phases

1. **Training pipeline.** Done. Loader, 15 features, stratified split, Random Forest, evaluation, `predict_url`, and unit tests live in `ml/`.
2. **Inference API.** Done. `POST /api/v1/predict` and `GET /health` live in `backend/`. The contract is in `API_SPECIFICATION.md`.
3. **LLM explainer.** Done. `POST /api/v1/predict` attaches `analysis` after the forest label. The call is skipped when the API key, base URL, or model name is empty.
4. **Next.js dashboard.** Done. `frontend/` submits a URL to `POST /api/v1/predict` and renders the returned label, risk level, probability, signals, features, and explanation.
5. **Analysis history.** Done. Each successful score is stored in SQLite. `GET /api/v1/history` lists recent rows, and `GET /api/v1/history/{id}` returns the saved detail.
6. **Security and reliability pass.** Done. The checks, residual risks, and how to run the suites are in `SECURITY.md`, `TESTING.md`, and `MODEL_LIMITATIONS.md`.
7. **Console and deployment preparation.** Done. The dashboard is a light analysis console. `DEPLOYMENT.md` is the manual runbook for Vercel and a Python host. Nothing in the repository deploys itself.

## Phase 1 results

`ml/models/metrics.json` holds the measured test scores, the selected hyperparameters, and the impurity importances. Read those numbers from that file or from `ML_PIPELINE.md`. They are not repeated here, because the HTTPS composition of this dataset changes how the scores should be explained.

Class medians are not stored. The API ranks signals with the saved impurity importances. Calibration of the forest's vote fractions has not been measured.

## References

- Prasad, A. & Chandra, S. (2024). PhiUSIIL Phishing URL (Website) [Dataset]. UCI Machine Learning Repository. https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
- Prasad, A., & Chandra, S. (2023). PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and incremental learning. *Computers & Security*, 103545. https://doi.org/10.1016/j.cose.2023.103545
- Prasad, Arvind; Chandra, Shalini (2023). "PhiUSIIL Phishing URL Dataset", Mendeley Data, V2. https://doi.org/10.17632/shwpxscxy2.2 — CC BY 4.0
- Mohammad, R., McCluskey, L., & Thabtah, F. (2015). *Phishing Websites* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C51W2X — prior art for URL properties such as IP host, "@", and length. That file is a pre-encoded feature matrix, so IntelliShield does not train on it.
