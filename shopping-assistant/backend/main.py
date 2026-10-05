"""
FastAPI + SQLite auth backend (JWT + bcrypt).

Install:  pip install fastapi uvicorn pyjwt bcrypt python-multipart
Run:      SECRET_KEY="long-random-string" uvicorn main:app --reload
Docs:     http://localhost:8000/docs  (you can test signup/login here)
"""

##NOTE: I did get this from claude, I will eventually go through this and learn how it works

import os
import sqlite3
import datetime as dt

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
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL
            )"""
        )
        # Example of a per-user table (saved items / wishlist)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS saved_items (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                item_id TEXT NOT NULL,
                title TEXT
            )"""
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
def search(q: str, user: dict = Depends(get_current_user)):
    # Replace with your real search_products(q, filters) call
    return {"user": user["username"], "query": q, "results": []}


@app.post("/saved")
def save_item(
    item_id: str,
    title: str = "",
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "INSERT INTO saved_items (user_id, item_id, title) VALUES (?, ?, ?)",
        (user["id"], item_id, title),
    )
    db.commit()
    return {"message": "Saved"}