# IntelliShield dashboard

Next.js page for `POST /api/v1/predict`. The page does not score URLs itself and does not hold an API key.

The layout and component responsibilities are in `docs/HLD.md` under Frontend architecture.

## Run

Start the API from `backend/` on port 8000, then from this directory:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000`. Copy `.env.example` if you need a different origin.

Production build and the Vercel steps are in `docs/DEPLOYMENT.md`. This directory does not publish itself.
