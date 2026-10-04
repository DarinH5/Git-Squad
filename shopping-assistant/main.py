"""Shopping Assistant backend (FastAPI + SQLite).

Run:   uvicorn main:app --reload          (serves http://127.0.0.1:8000)
Docs:  http://127.0.0.1:8000/docs

Env vars:
    DB_PATH   SQLite file path           (default: shopping_assistant.db)
    DEV_MODE  "1" = seed admin/password and return password-reset tokens in
              the API response (no email service yet). SET TO "0" IN PRODUCTION.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from scoring import extract_price, extract_rating, extract_review_count, host_from_url, score_product

DB_PATH = os.getenv("DB_PATH", "shopping_assistant.db")
DEV_MODE = os.getenv("DEV_MODE", "1") == "1"

SESSION_TTL = 60 * 60 * 24 * 7   # 7 days
RESET_TTL = 60 * 30              # 30 minutes
PBKDF2_ITERATIONS = 200_000
MAX_FAILED_LOGINS = 5
LOCKOUT_WINDOW = 60 * 10         # 10 minutes

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------- database
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                created_at    INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            """
        )
        if DEV_MODE:
            exists = conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone()
            if not exists:
                create_user(conn, "admin", "admin@example.com", "password")
                print("[DEV_MODE] Seeded demo user admin / password. Disable in production.")


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="Shopping Assistant API", lifespan=lifespan)


# ---------------------------------------------------------------- security
def hash_password(password: str, salt: Optional[bytes] = None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    candidate, _ = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, stored_hash)


def _hash_token(token: str) -> str:
    # Only hashes of tokens are stored, so a DB leak doesn't expose live sessions.
    return hashlib.sha256(token.encode()).hexdigest()


_failed_logins: dict = {}


def _check_throttle(key: str):
    now = time.time()
    recent = [t for t in _failed_logins.get(key, []) if now - t < LOCKOUT_WINDOW]
    _failed_logins[key] = recent
    if len(recent) >= MAX_FAILED_LOGINS:
        raise HTTPException(429, "Too many failed attempts. Please try again in a few minutes.")


def _record_failure(key: str):
    _failed_logins.setdefault(key, []).append(time.time())


# ---------------------------------------------------------------- helpers
def create_user(conn, username: str, email: str, password: str) -> int:
    pw_hash, salt = hash_password(password)
    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, email.lower(), pw_hash, salt, int(time.time())),
    )
    return cur.lastrowid


def create_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), user_id, now + SESSION_TTL),
    )
    return token


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters.")


def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not authenticated.")
    token_hash = _hash_token(authorization[7:].strip())
    with db() as conn:
        row = conn.execute(
            """SELECT u.id, u.username, u.email, s.expires_at
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ?""",
            (token_hash,),
        ).fetchone()
    if not row or row["expires_at"] < time.time():
        raise HTTPException(401, "Session expired. Please log in again.")
    user = dict(row)
    user["token_hash"] = token_hash
    return user


# ---------------------------------------------------------------- schemas
class SignupIn(BaseModel):
    username: str = Field(max_length=64)
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class LoginIn(BaseModel):
    username: str = Field(max_length=254)  # username or email
    password: str = Field(max_length=128)


class RecoverIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    new_password: str = Field(max_length=128)


# ---------------------------------------------------------------- auth routes
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/signup", status_code=201)
def signup(body: SignupIn):
    username, email = body.username.strip(), body.email.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(422, "Username must be 3-30 characters: letters, numbers, . _ -")
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    validate_password(body.password)
    try:
        with db() as conn:
            user_id = create_user(conn, username, email, body.password)
            token = create_session(conn, user_id)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "That username or email is already registered.")
    return {"token": token, "username": username}


@app.post("/auth/login")
def login(body: LoginIn):
    identifier = body.username.strip()
    key = identifier.lower()
    _check_throttle(key)
    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier)
        ).fetchone()
        if user:
            ok = verify_password(body.password, user["password_hash"], user["salt"])
        else:
            hash_password(body.password)  # burn equal time so we don't reveal which accounts exist
            ok = False
        if not ok:
            _record_failure(key)
            raise HTTPException(401, "Invalid username or password.")
        _failed_logins.pop(key, None)
        token = create_session(conn, user["id"])
    return {"token": token, "username": user["username"]}


@app.post("/auth/logout")
def logout(user: dict = Depends(current_user)):
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (user["token_hash"],))
    return {"message": "Logged out."}


@app.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return {"username": user["username"], "email": user["email"]}


@app.post("/auth/recover")
def recover(body: RecoverIn):
    """Always returns the same message so attackers can't probe which emails exist."""
    email = body.email.strip().lower()
    response = {"message": "If that email is registered, a reset link has been sent."}
    with db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(24)
            conn.execute("DELETE FROM reset_tokens WHERE user_id = ?", (user["id"],))
            conn.execute(
                "INSERT INTO reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_hash_token(token), user["id"], int(time.time()) + RESET_TTL),
            )
            # TODO: send `token` by email (SMTP / SendGrid / SES) instead of exposing it.
            if DEV_MODE:
                print(f"[DEV_MODE] Password reset token for {email}: {token}")
                response["reset_token"] = token
    return response


@app.post("/auth/reset")
def reset_password(body: ResetIn):
    validate_password(body.new_password)
    with db() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM reset_tokens WHERE token_hash = ?",
            (_hash_token(body.token.strip()),),
        ).fetchone()
        if not row or row["expires_at"] < time.time():
            raise HTTPException(400, "That reset token is invalid or has expired.")
        pw_hash, salt = hash_password(body.new_password)
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (pw_hash, salt, row["user_id"]),
        )
        conn.execute("DELETE FROM reset_tokens WHERE user_id = ?", (row["user_id"],))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))  # sign out everywhere
    return {"message": "Password updated. Please log in."}


# ---------------------------------------------------------------- products
_BUDGET_RE = re.compile(r"(?:under|below|less than|up to|around|max(?:imum)?(?: of)?)[^$0-9]{0,12}\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
_PRICE_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")


def interpret_shopping_query(query: str) -> dict:
    """Extract lightweight shopping intent without requiring an LLM/API key."""
    clean = " ".join(query.split())
    match = _BUDGET_RE.search(clean)
    budget_max = float(match.group(1).replace(",", "")) if match else None

    lower = clean.lower()
    feature_terms = [
        "noise cancellation", "wireless", "bluetooth", "waterproof", "portable",
        "gaming", "student", "college", "4k", "oled", "usb-c", "fast charging",
        "lightweight", "running", "office", "travel", "budget",
    ]
    features = [term for term in feature_terms if term in lower]

    search_query = clean
    if budget_max is not None and "buy online" not in lower:
        search_query += f" under ${budget_max:g}"
    if "buy online" not in search_query.lower():
        search_query += " buy online price"

    return {
        "original_query": clean,
        "budget_max": budget_max,
        "features": features,
        "search_query": search_query,
    }


def fetch_results(query: str) -> list:
    from ddgs import DDGS

    return DDGS().text(query, safesearch="moderate", max_results=10)


def _passes_budget(product: dict, budget_max: float | None) -> bool:
    if budget_max is None:
        return True
    price = product.get("signals", {}).get("price")
    # Keep products with no visible price; the score can still be useful and
    # the user can verify the live price on the retailer page.
    return price is None or price <= budget_max


@app.get("/products/search")
def search_products(
    q: str = Query(..., min_length=2, max_length=100),
    min_score: int = Query(0, ge=0, le=100),
    user: dict = Depends(current_user),
):
    intent = interpret_shopping_query(q.strip())
    try:
        raw = fetch_results(intent["search_query"])
    except Exception:
        raise HTTPException(502, "Product search is unavailable right now. Please try again.")

    products = []
    for item in raw or []:
        url = item.get("href", "")
        if not url.lower().startswith(("http://", "https://")):
            continue
        title = item.get("title") or "Shopping result"
        body = item.get("body") or ""
        scored = score_product(title, url, body)
        product = {
            "title": title,
            "url": url,
            "description": body,
            "retailer": host_from_url(url),
            "price": extract_price(f"{title} {body}"),
            "rating": extract_rating(f"{title} {body}"),
            "review_count": extract_review_count(f"{title} {body}"),
            **scored,
        }
        if product["score"] >= min_score and _passes_budget(product, intent["budget_max"]):
            products.append(product)

    products.sort(key=lambda p: p["score"], reverse=True)
    return {
        "query": intent["original_query"],
        "intent": intent,
        "count": len(products),
        "products": products,
    }
