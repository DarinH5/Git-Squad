"""
FastAPI + SQLite auth backend (JWT + bcrypt).

Install:  pip install fastapi uvicorn pyjwt bcrypt python-multipart
Run:      SECRET_KEY="long-random-string" uvicorn main:app --reload
Docs:     http://localhost:8000/docs  (you can test signup/login here)
"""
import os
import sqlite3
import datetime as dt
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")  # set a real one!
ALGORITHM = "HS256"
TOKEN_MINUTES = 60
DB_PATH = "shop.db"

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
                password_hash BLOB NOT NULL
            )"""
        )
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


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Auth helpers ----------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash)


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
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (body.username, hash_password(body.password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken")
    return {"message": "Account created"}


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


@app.get("/search")
def search(
    q: str = "",
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 12,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    sql = "SELECT * FROM products WHERE 1=1"
    args = []
    # Every word must appear somewhere (title, description, category, brand)
    for word in q.split():
        like = f"%{word}%"
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ? OR brand LIKE ?)"
        args += [like, like, like, like]
    if max_price is not None:
        sql += " AND price <= ?"
        args.append(max_price)
    if category:
        sql += " AND category = ?"
        args.append(category)
    sql += " ORDER BY rating DESC LIMIT ?"
    args.append(min(limit, 50))
    rows = db.execute(sql, args).fetchall()
    return {"query": q, "results": [dict(r) for r in rows]}


@app.get("/categories")
def categories(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return [r["category"] for r in rows]


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