# Shopwise AI — GitSquad Shopping Assistant

A personalized AI shopping assistant built with **Streamlit, FastAPI, SQLite, and optional Google Gemini**.

## Implemented features

- **API:** authenticated FastAPI endpoints with interactive OpenAPI docs at `/docs`.
- **Embedded shopping agents:** a request-intent stage, profile/preferences stage, product-research stage, and explainable ranking stage. The pipeline works with a local intent parser and optionally uses Gemini for richer natural-language interpretation.
- **Personalized profiles:** save a display name, budget range, preferred categories/brands/retailers, brands to avoid, interests, and additional shopping notes. Profile data is stored per account in SQLite.
- **Personalized recommendations:** searches use saved budgets and preference signals; product cards explain which preferences influenced their ranking.
- **UI refresh:** redesigned navigation, visual theme, shopping chat, product exploration, and profile editor.
- Existing account recovery, password change, product collections, and product catalog remain available.

The product catalog currently contains seeded demonstration products. Search and recommendation quality is limited by the products available in that catalog; connect a licensed product/search provider before presenting results as comprehensive live-market inventory.

## Run locally

Python 3.10+ recommended.

### 1. Install dependencies

From the `shopping-assistant` directory:

```bash
python -m venv .venv
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

Then:
```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env`. Set a unique `SECRET_KEY`. To enable Gemini-powered intent interpretation, add your own `GEMINI_API_KEY`. The shopping-agent workflow still runs without Gemini using the local intent parser.

```env
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=
DB_PATH=
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

Keep `.env` private and never commit API keys or production secrets.

### 3. Start the backend

Terminal 1:
```bash
cd backend
uvicorn main:app --reload
```

Backend:
- Health: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

### 4. Start the frontend

Terminal 2, from the `shopping-assistant` directory:
```bash
cd frontend
streamlit run app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501.

## API overview

All shopping/profile/collection routes require `Authorization: Bearer <access_token>` after signup or login.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health |
| POST | `/signup` | Create an account |
| POST | `/login` | Get a bearer token |
| GET | `/me` | Current account/profile |
| GET | `/me/profile` | Read saved shopping profile |
| PATCH | `/me/profile` | Update profile/preferences |
| GET | `/me/preferences` | Read recommendation preferences |
| POST | `/agents/shop` | Run the embedded shopping-agent workflow |
| POST | `/ai-search` | Gemini-backed intent search |
| GET | `/search` | Search catalog with profile-aware ranking |
| GET | `/categories` | List product categories |
| POST | `/projects` | Create a product collection |
| GET | `/projects` | List collections |
| GET | `/projects/{id}/items` | View collection items |
| POST | `/projects/{id}/items?product_id=...` | Save a product to a collection |
| DELETE | `/projects/{id}` | Delete a collection |

For exact request/response schemas, use `/docs`.

## How the embedded agents work

1. **Intent Agent** extracts the product terms and any budget in the request. Gemini is used when configured; otherwise a local parser handles common budget phrases.
2. **Profile Agent** loads the signed-in user's saved preferences.
3. **Product Research Agent** retrieves matching items from the local product catalog.
4. **Ranking Agent** applies explainable preference signals and returns reasons alongside the products.

The agents are currently implemented as an orchestrated backend workflow, not as independent autonomous services. This keeps the prototype easy to run and test while providing a clear extension point for specialized tools later.

## Database and existing accounts

The backend creates `backend/shop.db` automatically. Existing user databases are migrated by adding profile columns without deleting existing accounts or collections.

## Tests and checks

Compile-check the Python files:
```bash
python -m compileall backend frontend
```

Run the test suite if/when tests are present:
```bash
pytest -q
```

## Deployment notes

Before production deployment:
- Set a strong `SECRET_KEY` and disable development defaults.
- Use HTTPS and a managed database with backups.
- Configure CORS to only trusted frontend origins.
- Add rate limits and operational monitoring.
- Connect a real product data provider and verify product prices/availability at the retailer.
- Add an email provider for account recovery instead of relying on one-time recovery codes.
- Review privacy, retention, and consent requirements for saved user preferences.
