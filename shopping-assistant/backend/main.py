"""
FastAPI + SQLite auth backend (JWT + bcrypt).

Install:  pip install fastapi uvicorn pyjwt bcrypt python-multipart
Run:      SECRET_KEY="long-random-string" uvicorn main:app --reload
Docs:     http://localhost:8000/docs  (you can test signup/login here)
"""
import os
import re
import secrets
import sqlite3
import datetime as dt
from typing import Optional

import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import errors


import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-for-local-development-only")

ALGORITHM = "HS256"
TOKEN_MINUTES = 60
DB_PATH = "shop.db"

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)

app = FastAPI(title="Shopping Assistant API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ---------- Database ----------
SAMPLE_PRODUCTS = [
    ("Waterproof Hiking Boots", "Insulated boots for cold, wet trails", "footwear", "TrailCo", 89.99, 4.5),
    ("Trail Running Shoes", "Lightweight shoes with grippy soles", "footwear", "SprintX", 74.50, 4.3),
    ("Leather Chelsea Boots", "Classic everyday boots", "footwear", "Urbana", 129.00, 4.1),
    ("Insulated Winter Jacket", "Warm waterproof jacket for snow", "jackets", "NorthPeak", 159.99, 4.7),
    ("Packable Rain Jacket", "Ultralight shell that fits in a pocket", "jackets", "TrailCo", 64.99, 4.4),
    ("Fleece Pullover", "Soft midlayer for hiking and camping", "jackets", "NorthPeak", 49.99, 4.2),
    ("40L Hiking Backpack", "Waterproof pack with hip belt", "backpacks", "TrailCo", 94.00, 4.6),
    ("Daily Commuter Backpack", "Laptop sleeve and water bottle pocket", "backpacks", "Urbana", 59.95, 4.0),
    ("Wireless Earbuds", "Noise cancelling with 24 hour case", "electronics", "SoundWave", 79.99, 4.3),
    ("Portable Phone Charger", "10000mAh power bank, USB-C", "electronics", "VoltGo", 24.99, 4.5),
    ("Insulated Water Bottle", "Keeps drinks cold 24 hours", "kitchen", "HydroMax", 29.95, 4.8),
    ("Pour Over Coffee Set", "Glass dripper with reusable filter", "kitchen", "BrewCraft", 39.00, 4.4),
]


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                recovery_hash BLOB
            )"""
        )
        # Older databases were created without recovery_hash, so add it if it's missing
        user_columns = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
        if "recovery_hash" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN recovery_hash BLOB")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                brand TEXT,
                price REAL,
                rating REAL,
                image_url TEXT,
                product_url TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL
            )"""
        )
        # A product can be in a project only once (composite primary key)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS project_items (
                project_id INTEGER NOT NULL REFERENCES projects(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, product_id)
            )"""
        )
        # Seed sample data so the UI has something to show (replace with a real dataset later)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for i, (title, desc, cat, brand, price, rating) in enumerate(SAMPLE_PRODUCTS):
                conn.execute(
                    "INSERT INTO products (title, description, category, brand, price, rating, image_url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (title, desc, cat, brand, price, rating,
                     f"https://picsum.photos/seed/shop{i}/400/300"),
                )


init_db()


def get_db():
    # check_same_thread=False because FastAPI may use different threads
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------- Schemas ----------
class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class PasswordConfirm(BaseModel):
    password: str = Field(max_length=72)


class RecoverRequest(BaseModel):
    username: str = Field(max_length=32)
    recovery_code: str = Field(max_length=64)
    new_password: str = Field(min_length=8, max_length=72)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AISearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=12, ge=1, le=50)


# ---------- Auth helpers ----------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash)
    except ValueError:  # e.g. a password longer than bcrypt's 72-byte limit
        return False


def ensure_bcrypt_safe(password: str):
    """bcrypt only handles 72 bytes; accented or emoji characters use more than one byte each."""
    if len(password.encode()) > 72:
        raise HTTPException(status_code=422, detail="Password is too long")


# ---------- Recovery codes ----------
# Each account gets a one-time recovery code when it is created. It's shown to the user once,
# and only a bcrypt hash of it is stored (just like a password). A production app would email
# a reset link instead, but this works without any email setup.
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, which are easy to confuse


def new_recovery_code() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(16))  # about 80 bits of randomness
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))  # e.g. K7QM-2XD9-HV4T-PB8R


def normalize_code(code: str) -> str:
    """Ignore case, dashes, and spaces so users can type the code any way they like."""
    return re.sub(r"[^A-Za-z0-9]", "", code).upper()


def hash_recovery_code(code: str) -> bytes:
    return bcrypt.hashpw(normalize_code(code).encode(), bcrypt.gensalt())


def verify_recovery_code(code: str, code_hash: bytes) -> bool:
    try:
        return bcrypt.checkpw(normalize_code(code).encode(), code_hash)
    except ValueError:
        return False


# Used so a wrong username takes as long to reject as a wrong code (hides which usernames exist)
DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt())


def create_token(username: str) -> str:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": username, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: sqlite3.Connection = Depends(get_db)
):
    """Dependency: add `user = Depends(get_current_user)` to protect any route."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except jwt.PyJWTError:
        raise credentials_error
    row = db.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise credentials_error
    return dict(row)


# ---------- Routes ----------
@app.post("/signup", status_code=201)
def signup(body: SignupRequest, db: sqlite3.Connection = Depends(get_db)):
    ensure_bcrypt_safe(body.password)
    recovery_code = new_recovery_code()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, recovery_hash) VALUES (?, ?, ?)",
            (body.username, hash_password(body.password), hash_recovery_code(recovery_code)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")
    # The plain code is returned this one time only; the database keeps just its hash
    return {"message": "Account created", "recovery_code": recovery_code}


@app.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: sqlite3.Connection = Depends(get_db)
):
    row = db.execute(
        "SELECT password_hash FROM users WHERE username = ?", (form.username,)
    ).fetchone()
    # Same error for "no such user" and "wrong password" so attackers can't tell which
    if row is None or not verify_password(form.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=create_token(form.username))


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


# Change password while logged in. Needs the current password, so a stolen session can't lock you out.
# Returns 400 (not 401) for a wrong password, because the frontend treats 401 as "token expired".
@app.post("/me/password")
def change_password(
    body: PasswordChange,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    ensure_bcrypt_safe(body.new_password)
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
    if not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(body.new_password), user["id"]),
    )
    db.commit()
    return {"message": "Password changed"}


# Make a fresh recovery code (also how accounts created before this feature get their first one).
# The old code stops working.
@app.post("/me/recovery-code")
def regenerate_recovery_code(
    body: PasswordConfirm,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    code = new_recovery_code()
    db.execute("UPDATE users SET recovery_hash = ? WHERE id = ?", (hash_recovery_code(code), user["id"]))
    db.commit()
    return {"recovery_code": code}


# Forgot-password reset: no login needed, the recovery code proves who you are.
# The code is single use. A new one is issued after every successful reset.
@app.post("/recover")
def recover_password(body: RecoverRequest, db: sqlite3.Connection = Depends(get_db)):
    ensure_bcrypt_safe(body.new_password)
    row = db.execute(
        "SELECT id, recovery_hash FROM users WHERE username = ?", (body.username,)
    ).fetchone()
    stored = row["recovery_hash"] if row and row["recovery_hash"] else DUMMY_HASH
    code_ok = verify_recovery_code(body.recovery_code, stored)
    # One generic message for unknown user, no code on file, and wrong code
    if row is None or not row["recovery_hash"] or not code_ok:
        raise HTTPException(status_code=400, detail="Invalid username or recovery code")
    new_code = new_recovery_code()
    db.execute(
        "UPDATE users SET password_hash = ?, recovery_hash = ? WHERE id = ?",
        (hash_password(body.new_password), hash_recovery_code(new_code), row["id"]),
    )
    db.commit()
    return {"message": "Password reset", "recovery_code": new_code}


# ---------- Search helpers ----------
# Words that carry no meaning for matching ("show me boots" -> "boots")
FILLER_WORDS = {
    "a", "an", "the", "i", "me", "my", "some", "any", "show", "find", "get", "want", "need",
    "looking", "look", "for", "please", "something", "anything", "item", "items", "product",
    "products", "price", "priced", "cost", "costs", "costing", "dollar", "dollars", "bucks",
}
_NUM = r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)(?![A-Za-z])"  # a number, optional $, but not "40L"


def _num(text):
    return float(text.replace(",", ""))


def parse_search(q: str):
    """Split a search like 'boots under $100' into (words, shown_words, min_price, max_price).
    words are used for matching (plurals trimmed); shown_words are as the user typed them.

    Understands: under/below/less than/up to/max, over/above/more than/at least/min,
    'between 50 and 80', '$50-$80', 'around $60', a bare '$60' or '60 dollars', and a query
    that is only a number. Numbers without a $ or keyword (like '40L backpack') stay as text.
    """
    text, lo, hi = q, None, None

    def take(pattern):
        """Find a pattern, remove it from text, and return the match (or None)."""
        nonlocal text
        m = re.search(pattern, text, re.I)
        if m:
            text = text[:m.start()] + " " + text[m.end():]
        return m

    m = take(rf"\bbetween\s+{_NUM}\s*(?:and|to|-)\s*{_NUM}") or take(
        r"\$\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*\$?\s*(\d+(?:\.\d+)?)"
    )
    if m:
        lo, hi = sorted((_num(m.group(1)), _num(m.group(2))))

    m = take(rf"(?:\b(?:under|below|less than|cheaper than|up to|within|at most|max(?:imum)?)|<=?)\s*{_NUM}")
    if m:
        hi = _num(m.group(1))
    m = take(rf"(?:\b(?:over|above|more than|at least|min(?:imum)?)|>=?)\s*{_NUM}")
    if m:
        lo = _num(m.group(1))

    if lo is None and hi is None:  # "around $60", "$60", "60 dollars", or just "60"
        m = (
            take(rf"(?:\b(?:around|about|near|roughly|approximately)|~)\s*{_NUM}")
            or take(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)")
            or take(r"\b(\d+(?:\.\d+)?)\s*(?:dollars?|bucks)\b")
            or (re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text) and take(r"(\d+(?:\.\d+)?)"))
        )
        if m:
            target = _num(m.group(1))
            lo, hi = round(target * 0.75, 2), round(target * 1.25, 2)

    words, shown = [], []
    for w in re.findall(r"[A-Za-z0-9']+", text):
        if w.lower() in FILLER_WORDS:
            continue
        shown.append(w)
        if len(w) > 3 and w.lower().endswith("s"):  # crude plural handling: boots -> boot
            w = w[:-1]
        words.append(w)
    return words, shown, lo, hi


def search_products(db, q="", min_price=None, max_price=None, category=None, limit=12):
    """The one place that searches the products table. Used by /search and by the AI agent."""
    words, shown, parsed_lo, parsed_hi = parse_search(q)
    # Explicit parameters (from the Browse page filters) win over prices typed in the text
    lo = min_price if min_price is not None else parsed_lo
    hi = max_price if max_price is not None else parsed_hi

    sql = "SELECT * FROM products WHERE 1=1"
    args = []
    # Every word must appear somewhere (title, description, category, brand)
    for word in words:
        like = f"%{word}%"
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ? OR brand LIKE ?)"
        args += [like, like, like, like]
    if lo is not None:
        sql += " AND price >= ?"
        args.append(lo)
    if hi is not None:
        sql += " AND price <= ?"
        args.append(hi)
    if category:
        sql += " AND category = ?"
        args.append(category)
    sql += " ORDER BY rating DESC LIMIT ?"
    args.append(min(limit, 50))
    rows = db.execute(sql, args).fetchall()
    return {
        "query": q,
        "applied": {"text": " ".join(shown), "min_price": lo, "max_price": hi},
        "results": [dict(r) for r in rows],
    }

def interpret_search_query(query, categories):
    """
    Uses Gemini to interpret a user's shopping request.

    Extracts:
    - Product keywords
    - Minimum price
    - Maximum price
    - Product category
    - Explanation of the request
    """

    if gemini_client is None:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured."
        )

    prompt = f"""
    You are an AI shopping assistant.

    Interpret the user's shopping request and extract the information
    needed to search a product database.

    Available categories:
    {categories}

    Return ONLY a JSON object with these fields:

    {{
        "keywords": "product search keywords",
        "min_price": null,
        "max_price": null,
        "category": null,
        "explanation": "brief explanation"
    }}

    Rules:
    - Only use categories from the available category list.
    - Use null when no price limit is specified.
    - Under $100 means max_price = 100.
    - Over $50 means min_price = 50.
    - Extract both limits when a range is specified.
    - Keywords should describe the product, not the entire sentence.
    - Do not invent products.
    - Do not include price information in keywords.

    User request: {query}
    """

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise ValueError("Gemini returned an invalid response.")

        return result

    except errors.APIError as e:
        print(f"Gemini API error: {e.code} - {e.message}")

        if e.code == 503:
            raise HTTPException(
                status_code=503,
                detail="Gemini is temporarily unavailable. Try again shortly."
            )

        raise HTTPException(
            status_code=502,
            detail="There was a problem communicating with Gemini."
        )

    except (ValueError, TypeError, AttributeError) as e:
        print("Invalid Gemini response:", e)

        raise HTTPException(
            status_code=502,
            detail="Gemini returned an invalid search interpretation."
        )

    except Exception as e:
        print("Unexpected Gemini error:", e)

        raise HTTPException(
            status_code=500,
            detail="The AI assistant could not interpret your request."
        )

@app.get("/search")
def search(
    q: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 12,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    return search_products(db, q, min_price, max_price, category, limit)


@app.get("/categories")
def categories(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return [r["category"] for r in rows]

@app.post("/ai-search")
def ai_search(
    body: AISearchRequest,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    # Get categories from the database
    category_rows = db.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()

    categories = [
        row["category"]
        for row in category_rows
        if row["category"]
    ]

    # Ask Gemini to interpret the request
    filters = interpret_search_query(body.query, categories)

    keywords = filters.get("keywords", "")
    category = filters.get("category")
    min_price = filters.get("min_price")
    max_price = filters.get("max_price")

    # Validate Gemini's returned values
    if not isinstance(keywords, str):
        raise HTTPException(
            status_code=502,
            detail="Invalid keywords returned by Gemini."
        )

    if category not in categories:
        category = None

    try:
        min_price = float(min_price) if min_price is not None else None
        max_price = float(max_price) if max_price is not None else None
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Invalid price filters returned by Gemini."
        )

    if (
        (min_price is not None and min_price < 0)
        or (max_price is not None and max_price < 0)
        or (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        )
    ):
        raise HTTPException(
            status_code=502,
            detail="Gemini returned an invalid price range."
        )

    # Use your existing search_products() function!
    results = search_products(
        db=db,
        q=keywords,
        min_price=min_price,
        max_price=max_price,
        category=category,
        limit=body.limit
    )

    return {
        "query": body.query,
        "interpretation": filters.get("explanation", ""),
        "applied": {
            "keywords": keywords,
            "min_price": min_price,
            "max_price": max_price,
            "category": category
        },
        "results": results["results"]
    }


# ---------- Projects (named groups of products) ----------
def get_owned_project(db, project_id, user_id):
    """Return the project row, or 404. Also stops users from touching each other's projects."""
    row = db.execute(
        "SELECT id, name FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


@app.post("/projects", status_code=201)
def create_project(
    body: ProjectCreate,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name can't be blank")
    cur = db.execute("INSERT INTO projects (user_id, name) VALUES (?, ?)", (user["id"], name))
    db.commit()
    return {"id": cur.lastrowid, "name": name}


@app.get("/projects")
def list_projects(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    # One row per project, with the item count and the sum of its products' prices
    rows = db.execute(
        "SELECT p.id, p.name, COUNT(pi.product_id) AS item_count, "
        "COALESCE(SUM(pr.price), 0) AS total_price "
        "FROM projects p "
        "LEFT JOIN project_items pi ON pi.project_id = p.id "
        "LEFT JOIN products pr ON pr.id = pi.product_id "
        "WHERE p.user_id = ? GROUP BY p.id ORDER BY p.id",
        (user["id"],),
    ).fetchall()
    projects = [dict(r) for r in rows]

    # Thumbnails: image URLs of the items in each project (newest first)
    image_rows = db.execute(
        "SELECT pi.project_id, pr.image_url FROM project_items pi "
        "JOIN products pr ON pr.id = pi.product_id "
        "JOIN projects p ON p.id = pi.project_id "
        "WHERE p.user_id = ? AND pr.image_url IS NOT NULL AND pr.image_url != '' "
        "ORDER BY pi.added_at DESC, pi.rowid DESC",
        (user["id"],),
    ).fetchall()
    images = {}
    for r in image_rows:
        images.setdefault(r["project_id"], []).append(r["image_url"])

    for p in projects:
        p["total_price"] = round(p["total_price"], 2)
        p["thumbnails"] = images.get(p["id"], [])[:4]
    return projects


@app.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    get_owned_project(db, project_id, user["id"])
    db.execute("DELETE FROM project_items WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    return {"message": "Project deleted"}


@app.get("/projects/{project_id}/items")
def list_project_items(
    project_id: int,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    project = get_owned_project(db, project_id, user["id"])
    rows = db.execute(
        "SELECT p.* FROM project_items pi JOIN products p ON p.id = pi.product_id "
        "WHERE pi.project_id = ? ORDER BY pi.added_at DESC, pi.rowid DESC",
        (project_id,),
    ).fetchall()
    return {"project": dict(project), "results": [dict(r) for r in rows]}


@app.post("/projects/{project_id}/items", status_code=201)
def add_project_item(
    project_id: int,
    product_id: int,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    get_owned_project(db, project_id, user["id"])
    if db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Product not found")
    cur = db.execute(
        "INSERT OR IGNORE INTO project_items (project_id, product_id) VALUES (?, ?)",
        (project_id, product_id),
    )
    db.commit()
    return {"message": "Added" if cur.rowcount else "Already in project"}


@app.delete("/projects/{project_id}/items/{product_id}")
def remove_project_item(
    project_id: int,
    product_id: int,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    get_owned_project(db, project_id, user["id"])
    db.execute(
        "DELETE FROM project_items WHERE project_id = ? AND product_id = ?", (project_id, product_id)
    )
    db.commit()
    return {"message": "Removed"}