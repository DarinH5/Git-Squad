# GitSquad AI Shopping Assistant

An AI-style shopping assistant prototype built with **Streamlit + FastAPI + SQLite**.
It lets authenticated users search for products, interprets simple shopping intent such as budgets/features, ranks results with a transparent 0–100 quality heuristic, and explains why each result received its score.

## Architecture

```text
Streamlit UI
    |
    | HTTP + Bearer session token
    v
FastAPI backend
    |-- Authentication + sessions
    |-- Password recovery (development token flow)
    `-- Product search + ranking
             |
             v
        DuckDuckGo search
             |
             v
       Product signals
       (seller, price,
        rating, reviews)
             |
             v
       Quality score 0-100
```

> **Important:** The product score is a transparent estimate from visible search-result signals. It is not a guarantee that a product is high quality.

## 1. Install

Python 3.10+ is recommended.

```bash
cd shopping-assistant
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Start the backend

From the `shopping-assistant` directory:

```bash
uvicorn main:app --reload
```

Check:

```text
http://127.0.0.1:8000/health
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## 3. Start the Streamlit app

Open a second terminal in the same directory and activate the same virtual environment.

```bash
streamlit run app.py
```

Open the URL Streamlit prints, normally:

```text
http://localhost:8501
```

## Demo account

When `DEV_MODE=1`, the backend seeds:

```text
username: admin
password: password
```

This is for local development/demo use only.

## Sprint demo flow

1. Open the app and log in.
2. Open **Chatbot**.
3. Search for something specific, for example:
   `wireless headphones under $150 with noise cancellation`
4. Show that the assistant identifies the budget/features.
5. Show the ranked products and 0–100 scores.
6. Expand **Why this score?** to show source trust, rating, reviews, HTTPS, price, and warnings.
7. Click a product to verify the live listing.

## Authentication

Implemented endpoints:

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/recover`
- `POST /auth/reset`

Passwords use PBKDF2-HMAC-SHA256 with per-user salts. Session and reset tokens are stored hashed.

Password recovery currently exposes a reset token only in `DEV_MODE`; production email delivery should be added before deployment.

## Product API

`GET /products/search?q=<query>&min_score=<0-100>` requires a valid Bearer session token.

The response contains:

- interpreted shopping intent
- ranked products
- retailer/domain
- visible price when found
- visible rating when found
- review count when found
- score and label
- score breakdown
- human-readable reasons

## Tests

Run:

```bash
pytest -q
```

## Project layout

```text
app.py                 Streamlit entry point
api_client.py          Frontend-to-backend HTTP client
main.py                FastAPI backend
scoring.py             Product quality scoring
components.py          Shared UI/theme
pages/                 Active Streamlit pages
images/                Active app assets
tests/                 Automated tests
```

The older `frontend/` tree is retained for historical/team reference. **Use the root `app.py` and root `pages/` implementation for the current application and sprint demo.**
