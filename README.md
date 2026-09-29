# IntelliShield

Phishing Detection & URL Threat Analysis Platform

## About

IntelliShield checks a URL for signs of phishing. You submit an address, and the app measures the URL text. It does not open the page. A Random Forest model then labels the URL safe or phishing. An LLM can add an explanation and recommendations. That text describes the model result. It does not change the label.

## Features

- URL feature extraction from the address itself (length, HTTPS, IP host, keywords, and similar measurements)
- Random Forest classification: safe or phishing
- Confidence for the returned label, and a low, medium, or high risk level
- Threat signals for the URL, plus the full set of feature values
- An LLM explanation and recommendations when an API key is set
- A fallback explanation from the classifier output when the key is not set
- Saved analysis history in SQLite

## Tech Stack

- Next.js
- Tailwind CSS
- Python
- FastAPI
- Scikit-learn
- Random Forest
- LLM
- SQLite with SQLAlchemy

## How It Works

```text
User enters a URL
→ FastAPI receives it
→ URL features are extracted
→ Random Forest predicts safe or phishing
→ An explanation and recommendations are attached
```

## Running Locally

You need Python 3.13 and Node.js. The trained model is already in `ml/models/phishing_rf.joblib`, so you do not have to train it to try the app.

Clone the repository and open the project folder.

Backend, from `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 8000
```

Leave `OPENAI_API_KEY` empty in `backend/.env` if you only want the classifier. Set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` if you want the LLM explanation.

Frontend, from `frontend/` in another terminal:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. The dashboard calls http://localhost:8000 unless you change `NEXT_PUBLIC_API_BASE_URL`.

## Project Structure

```text
frontend/    Next.js dashboard
backend/     FastAPI app
ml/          feature code, training, and the saved model
```

## Notes / Limitations

The model only sees the URL string. A safe label is not proof that a site is safe to use, and a phishing label is not a look at the page itself.

It was trained on the PhiUSIIL phishing URL dataset. Results on that file are not the same thing as results on arbitrary links from the internet.

There are no user accounts. History is whatever the API process has stored in its SQLite file.

## Future Improvements

- Use more than the URL string, such as redirects or page content
- Test the model on URLs that were not in the training set
- Separate history by user, instead of one shared local database
