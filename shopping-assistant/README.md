# Shopwise AI — GitSquad Shopping Assistant

A personalized shopping assistant built with **Streamlit, FastAPI, SQLite, and optional Google Gemini**.

## Active application entry points

The integrated application is `backend/main.py` (FastAPI) plus `frontend/app.py` (Streamlit).
Run the backend from `backend/` and the frontend from `frontend/` as shown below. The
root-level `app.py` and `main.py` are retained legacy prototypes and are not the active
full-stack entry points.

## Features

- Authenticated API with JWT-based sessions and interactive FastAPI docs.
- AI shopping workflow with intent, profile, catalog-research, and ranking stages.
- Deterministic local intent parsing works without an LLM key; Gemini is optional and falls back safely when unavailable.
- Profile-aware recommendations with an explainable 0–100 match score.
- Product browsing with category and budget filters.
- Product collections and saved shopping searches.
- Account creation, login, password changes, and recovery-code reset.
- Per-user saved profile preferences and theme selection.
- Automated tests and GitHub Actions CI workflow.

**Product data note:** the current catalog is seeded demonstration data in SQLite. It is not a live retailer feed and does not guarantee current prices or availability. Before describing results as live inventory, connect a licensed product/retailer data provider and validate its terms, attribution, price freshness, and purchase URLs.

## Run locally

Python 3.10+ recommended.

### 1. Install dependencies

From `shopping-assistant`:

```bash
python -m venv .venv
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\\Scripts\\Activate.ps1
```

Then:
```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and set a unique `SECRET_KEY`. `GEMINI_API_KEY` is optional.

```env
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=
DB_PATH=
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

Never commit `.env` or production secrets.

### 3. Start the backend

Terminal 1:
```bash
cd backend
uvicorn main:app --reload
```

API health: http://127.0.0.1:8000/health  
Interactive API docs: http://127.0.0.1:8000/docs

### 4. Start the frontend

Terminal 2, from `shopping-assistant`:
```bash
cd frontend
streamlit run app.py
```

Open the URL printed by Streamlit (normally http://localhost:8501).

## API overview

Authenticated routes require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/signup` / `/login` | Create account / sign in |
| GET | `/me` / `/me/profile` | Read account and preferences |
| PATCH | `/me/profile` | Update profile and theme |
| POST | `/agents/shop` | Run the orchestrated shopping workflow |
| POST | `/ai-search` | Interpret and search a shopping request |
| GET | `/search` | Search and rank the catalog |
| GET | `/categories` | List catalog categories |
| GET/POST | `/saved-searches` | List or save a search |
| DELETE | `/saved-searches/{id}` | Delete a saved search |
| POST | `/projects` | Create a product collection |
| GET | `/projects` | List collections |
| GET | `/projects/{id}/items` | View collection items |
| POST | `/projects/{id}/items?product_id=...` | Save a product to a collection |
| DELETE | `/projects/{id}` | Delete a collection |

Use `/docs` for exact schemas and interactive requests.

## Testing

From this directory:
```bash
python -m compileall -q backend frontend
pytest -q
```

The test suite covers local intent parsing, agent orchestration, product score bounds, and extraction of price/rating/review signals. GitHub Actions runs these checks on pushes and pull requests that change `shopping-assistant`.

## Web deployment (Render)

A repository-root `render.yaml` blueprint is included. It defines:
- FastAPI backend with a persistent disk for SQLite.
- Streamlit frontend configured to call the backend.
- A generated `SECRET_KEY`.
- A health check at `/health`.

To deploy:
1. Push the updated repository to GitHub.
2. In Render, create a new Blueprint and select the repository.
3. Confirm the two services and persistent disk in the blueprint.
4. Add `GEMINI_API_KEY` to the backend service only if you want Gemini-enhanced interpretation.
5. After the frontend service is created, confirm its public URL and update the backend `CORS_ORIGINS` environment variable to that exact URL.
6. Confirm the frontend `BACKEND_URL` points to the backend service's public URL.
7. Deploy and test signup, login, AI search, browse, collections, saved searches, and profile updates.

Render's persistent disk may require a paid plan. Do not use an ephemeral filesystem for the SQLite production database. For a larger deployment, use managed PostgreSQL, HTTPS, rate limiting, monitoring, backups, and a verified product-data provider.

## Security and production checklist

- Set a unique production `SECRET_KEY`; never use the development fallback.
- Restrict CORS to the actual frontend origin.
- Keep API keys in hosting environment variables.
- Use HTTPS and persistent, backed-up database storage.
- Add email-based account recovery before relying on this for real users; recovery codes are currently a manual fallback.
- Add rate limiting and monitoring to public endpoints.
- Connect a licensed live product provider before claiming live retailer pricing or availability.
- Review privacy and retention requirements for saved profile preferences.
