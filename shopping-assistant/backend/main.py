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


import bcrypt #used to hash passwords
import jwt #deals with login tokens

from fastapi import Depends, FastAPI, HTTPException, status 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")  # set a real one!
ALGORITHM = "HS256"
TOKEN_MINUTES = 60
DB_PATH = "shop.db" # Path to the SQLite database file, saves all application data

app = FastAPI(title="Shopping Assistant API") #Create the FastAPI app
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login") # Helper for handling OAuth2 password flow

#Sample database, need to replace with a real dataset later
#Find a shopping product API to populate the database with real data later

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

# Creates the database and initializes the tables for users, saved items, and products
# DB_PATH points to the SQLite database file used for storing all the data.
# We run conn.execute 3 times to create the users, saved_items, and products tables.
# This is only called once to initialize the database.
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Create the users table if it doesn't exist
        # if it does exist, the program skips this and goes to the next table,
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
        # Seed sample data so the UI has something to show (replace with a real dataset later)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for i, (title, desc, cat, brand, price, rating) in enumerate(SAMPLE_PRODUCTS):
                conn.execute(
                    "INSERT INTO products (title, description, category, brand, price, rating, image_url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (title, desc, cat, brand, price, rating,
                     f"https://picsum.photos/seed/shop{i}/400/300"),
                )

#Call the init_db function to create the database and tables if they don't exist
init_db()

# This is called every time the API needs to access the database
# yield is used to provide the database connection to the API routes, it pauses the function 
# and yields the connection, this is good for managing database connections efficiently
def get_db():
    # check_same_thread=False because FastAPI may use different threads
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------- Schemas ----------
# Used for defining the structure of signup requests and authentication tokens.
# Essentially creates username and password requirements for user signup.
# Checks incoming JSON data against the defined schema.
class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


# This is used for defining the structure of authentication tokens.
# returns a dictionary containing the access token and token type
# used for logging in users
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Auth helpers ----------

# Hashes the user's password using bcrypt for secure storage.
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verifies the user's password against the stored bcrypt hash.
def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash)


# HTTP has no memory, so when you login the server gives you a token and you use this token
# with each subsequent request to authenticate yourself.
# The token is a JWT, with a payload containing the username and expiration time.
# A payload is the part of the JWT that contains the actual data.
# The token is signed with a secret key to ensure its integrity, so if anyone changes
# the user information, the token will become invalid.
# USES THE SECRET_KEY above, so keep it secure
def create_token(username: str) -> str:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": username, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)

# Gets the current authenticated user based on the provided JWT token using the OAuth2 scheme.
# Looks to see if the signature or expiration time is invalid.
# Returns a dictionary containing the user's id and username if the token is valid.
# Called every time a request is made that requires authentication.
def get_current_user(
    token: str = Depends(oauth2_scheme), db: sqlite3.Connection = Depends(get_db)
):
    """Dependency: add `user = Depends(get_current_user)` to protect any route."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Try to decode the JWT token
    # Error checks the signature and expiration time
    # row = db.execute() purpose is to fetch the user's information from the database
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

#POST sends data and GET retrieves data.

# Defines the API routes for user authentication and product search.
#app.post("/signup") - Handles user signup requests.
#   the "/signup" is seen in the URL when a user attempts to create a new account.
# this signals the user is on the signup page.
# The signup route expects a POST request with the user's username and password.
# Inserts a new user into the database with the provided username and hashed password.
# db.commit() is called to save the changes to the database.

# Signup route for creating a new user account.
# Recieves a post request with the user's username and password.
# Gets username/password from SignupRequest
# stores the username/hashed password in the database
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

#app.post("/login") - Handles user login requests.
# Recieves a post request from the frontend
# Finds the username in the database
# fetchone() returns the first row of the result set, which contains the user's password hash
# if username is not found or password is incorrect, raise an error
# Calls access_token to create a new token for the authenticated user
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

# Retrieve the currently authenticated user's information
# This is used to get the user's details once they are logged in
@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user

# When a get request is made from the frontend, this route handles the search functionality
#Defines the format for a search request
# Searches through the products table and filters based on the provided criteria
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

# Retrieve a list of all unique product categories
# Used to filter products by category
@app.get("/categories")
def categories(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return [r["category"] for r in rows]

# When a user wants to save an item, a post request is sent to this endpoint
# this saves the item to the user's saved items list
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