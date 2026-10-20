"""
FastAPI + SQLite auth backend (JWT + bcrypt).

Install:  pip install fastapi uvicorn pyjwt bcrypt python-multipart
Run:      SECRET_KEY="long-random-string" uvicorn main:app --reload
Docs:     http://localhost:8000/docs  (you can test signup/login here)
"""

#What is my backend framework?
# FastAPI is being used as the backend framework.
# What is my database?
# SQLite is being used as the database.
# How does Sqlite work?
# SQLite is a self-contained, serverless, zero-configuration, transactional SQL database engine.
# It stores the entire database as a single file on disk and allows access through SQL queries.

# Does this work because this website doesn't really have users interact with others? Whereas like if I could view
# some elses profile, I would need to do something else?
# In this case, since users are mostly interacting with products and 
# their own projects, the current setup is sufficient.
# Once I get an api with shopping products can sqlite handle that?
# SQLite can handle a moderate amount of traffic and data, 
# but for very high traffic or large datasets, a more robust database like PostgreSQL might be needed.
#How much would that change code?
# Switching from SQLite to PostgreSQL would mainly involve changing the database connection setup and SQL syntax where necessary.
# You might also use an ORM like SQLAlchemy to make the transition smoother and database-agnostic.
# FOr now though, sqlite is sufficient?

#Steamlit is the frontend framework being used 
# for building the user interface of the shopping assistant website.
# Its a python library that allows for the creation of 
# interactive web applications directly from Python code.

import os
import sqlite3
import datetime as dt
from typing import Optional

import bcrypt
import re 
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
    #Fast api is the web framework being used for building the backend API.
    # It handles routing, request parsing, response formatting, and
    # integrates with other components like authentication and database access.
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field  # ensures that the incoming data matches the expected structure and types for these operations.

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")  # set a real one!
ALGORITHM = "HS256"
TOKEN_MINUTES = 60
DB_PATH = "shop.db"

app = FastAPI(title="Shopping Assistant API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ---------- Database ----------
# WHat would a real database look like?
# Would it be like Products = [api key]? or something like that?

# Where are the pictures coming from? WHen i look at them there are placeholder images that dont relate
# They might be coming from a static folder or an external image hosting service.
# Are you using picsum to generate pictures?

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

#Create requirements for API requests and responses
#Used to format and validate the structure of API requests and responses
#Pydantic will automatically convert the request body to the appropriate Python types and validate it.
class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ResetPasswordRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    new_password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


# ---------- Auth helpers ----------

#THese are used to hash and verify passwords, and to create JWT tokens for authentication.
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash)


def create_token(username: str) -> str:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": username, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)

# ---------- User helpers ----------
# This retrieves the current user based on the JWT token provided in the Authorization header.
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

# Handles user signup and account creation.
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

# Handles user login and returns an access token.
# THis access token is a JWT that must be included in the Authorization header for protected routes.
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

# Will be used to get the current user's information.
@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


# Used to search for products based on query, price, and category.
# ---------- Search helpers ----------

# Words that carry no meaning for matching ("show me boots" -> "boots")
FILLER_WORDS = {
    "a", "an", "the", "i", "me", "my", "some", "any", "show", "find", "get", "want", "need",
    "looking", "look", "for", "please", "something", "anything", "item", "items", "product",
    "products", "price", "priced", "cost", "costs", "costing", "dollar", "dollars", "bucks",
}

# Used to match numbers in search queries, optionally preceded by a dollar sign.
# 1,000 or $1,000.00 become 1000.0
_NUM = r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)(?![A-Za-z])"  # a number, optional $, but not "40L"
 
# Used to convert a matched number string into a float.
# _NUM finds numbers in the text, optionally preceded by a dollar sign. and _num turn them into floats.
# 1,000 -> 1000
def _num(text):
    return float(text.replace(",", ""))
 
# Parses a search query into words, shown words, and price range.
def parse_search(q: str):
    """Split a search like 'boots under $100' into (words, shown_words, min_price, max_price).
    words are used for matching (plurals trimmed); shown_words are as the user typed them.
 
    Understands: under/below/less than/up to/max, over/above/more than/at least/min,
    'between 50 and 80', '$50-$80', 'around $60', a bare '$60' or '60 dollars', and a query
    that is only a number. Numbers without a $ or keyword (like '40L backpack') stay as text.
    """
    # Initialize the text and price range variables.
    # text holds the remaining query after extracting price information.
    # lo and hi represent the minimum and maximum prices
    text, lo, hi = q, None, None

    # This helper function searches for a pattern in the text, removes it if found, and returns the match.
    # example: if text is "under $100 boots", take(rf"under\s*{_NUM}") 
    # will return the match for "under $100" and remove it from text.
    def take(pattern):
        """Find a pattern, remove it from text, and return the match (or None)."""
        nonlocal text
        m = re.search(pattern, text, re.I)
        if m:
            text = text[:m.start()] + " " + text[m.end():]
        return m

    # Look for a "between X and Y" or "$X-$Y" pattern to determine the price range.
    m = take(rf"\bbetween\s+{_NUM}\s*(?:and|to|-)\s*{_NUM}") or take(
        r"\$\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*\$?\s*(\d+(?:\.\d+)?)"
    )

    # If a "between" or range pattern was found, set the low and high prices accordingly.
    if m:
        lo, hi = sorted((_num(m.group(1)), _num(m.group(2))))
 
    # Look for "under", "below", "less than", etc., to set the maximum price.
    m = take(rf"(?:\b(?:under|below|less than|cheaper than|up to|within|at most|max(?:imum)?)|<=?)\s*{_NUM}")
    if m:
        hi = _num(m.group(1))

    # Look for "over", "above", "more than", etc., to set the minimum price.
    m = take(rf"(?:\b(?:over|above|more than|at least|min(?:imum)?)|>=?)\s*{_NUM}")

    # If a minimum price pattern was found, set the low price accordingly.
    if m:
        lo = _num(m.group(1))
 
    # If no explicit min or max price was found, look for approximate or bare price mentions.
    # If an approximate or bare price mention is found, set both the low and high prices around that value.
    if lo is None and hi is None:
        m = (
            take(rf"(?:\b(?:around|about|near|roughly|approximately)|~)\s*{_NUM}")
            or take(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)")
            or take(r"\b(\d+(?:\.\d+)?)\s*(?:dollars?|bucks)\b")
            or (re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", text) and take(r"(\d+(?:\.\d+)?)"))
        )
        # If a match was found, calculate the low and high prices as 75% and 125% of the target value.
        if m:
            target = _num(m.group(1))
            lo, hi = round(target * 0.75, 2), round(target * 1.25, 2)

    # Return the parsed words, the words shown to the user, and the determined price range.
    # words: the meaningful words extracted from the search text
    # shown: the words shown to the user (including filler words)
    words, shown = [], []

    # TThis loop extracts meaningful words from the search text, 
    # ignoring filler words and handling crude plural forms.
    for w in re.findall(r"[A-Za-z0-9']+", text):
        if w.lower() in FILLER_WORDS:
            continue
        shown.append(w)

        #This deals with plural forms of words, e.g., "boots" -> "boot"
        if len(w) > 3 and w.lower().endswith("s"):
            w = w[:-1]
        words.append(w)

    # Return the final list of meaningful words, the words shown to the user, and the determined price range.
    return words, shown, lo, hi
 
 # Endpoint for searching products based on query, price range, category, and other filters.
@app.get("/search")
def search(

    # Query parameters for the search endpoint.
    q: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 12,
    user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    # Parse the search query to extract meaningful words and determine a price range.
    # Uses the parse_search function to extract meaningful words and determine a price range.
    words, shown, parsed_lo, parsed_hi = parse_search(q)

    # Explicit parameters (from the Browse page filters) win over prices typed in the text
    lo = min_price if min_price is not None else parsed_lo
    hi = max_price if max_price is not None else parsed_hi

    # Construct the SQL query based on the parsed words, price range, and category.
    # A sql query is a string that will be executed against the database, with placeholders for parameters.
    # args is the list of parameters that will be substituted into the SQL query placeholders.
    sql = "SELECT * FROM products WHERE 1=1"
    args = []

    # Every word must appear somewhere (title, description, category, brand)

    # For each meaningful word, add a condition to the SQL query to 
    # match it against title, description, category, and brand.

    for word in words:
        # This takes a word such as "boot" and turns it into "%boot%" for the SQL LIKE query.
        #like = f"%{word}%" is the pattern used for the SQL LIKE query.
        #sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ? OR brand LIKE ?)" 
        # is the condition added to the SQL query for this word.
        #args += [like, like, like, like] is the list of parameters for the SQL query placeholders.

        like = f"%{word}%"
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ? OR brand LIKE ?)"
        args += [like, like, like, like]

    # Add conditions for the price range and category filters to the SQL query.
    #   If low price is specified, add a minimum price condition to the SQL query.
    #   If high price is specified, add a maximum price condition to the SQL query.
    #   If a category is specified, add a category condition to the SQL query.
    if lo is not None:
        sql += " AND price >= ?"
        args.append(lo)
    if hi is not None:
        sql += " AND price <= ?"
        args.append(hi)
    if category:
        sql += " AND category = ?"
        args.append(category)

    # Add the ORDER BY and LIMIT clauses to the SQL query.
    # This ensures that the results are sorted by rating in descending order 
    # and limits the number of results returned.
    sql += " ORDER BY rating DESC LIMIT ?"
    args.append(min(limit, 50))
    rows = db.execute(sql, args).fetchall()

    # Return the search results as a JSON object.
    # The JSON object includes the original query, the applied filters, and the search results.
    return {
        "query": q,
        "applied": {"text": " ".join(shown), "min_price": lo, "max_price": hi},
        "results": [dict(r) for r in rows],
    }

# Lists all product categories available in the store.
# Used by the frontend to populate category filters.
@app.get("/categories")
def categories(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    return [r["category"] for r in rows]


# ---------- Projects (named groups of products) ----------

# Helper function to get a project owned by the current user
# Returns the project row if it exists and belongs to the current user, otherwise raises a 404 error.
def get_owned_project(db, project_id, user_id):
    """Return the project row, or 404. Also stops users from touching each other's projects."""
    row = db.execute(
        "SELECT id, name FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row

# Posts a request to create a new project
# Returns the newly created project with its ID and name.
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

# Lists all projects owned by the current user, including item counts, total prices, and thumbnails.
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


# Deletes a project owned by the current user, including all its items.
# Returns a message indicating the deletion status.
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


# Lists all items in a specific project owned by the current user.
# Returns the project details along with its items.
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

# Project item management endpoints
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

# Account recovery section
# Function to check if a username exists in the users table of shop.db
def username_exists(username):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()
    conn.close()

    return user is not None

# Endpoint to check if a username exists
@app.get("/check-username/{username}")
def check_username(username: str):
    if not username_exists(username):
        raise HTTPException(
            status_code=404,
            detail="Username not found"
        )

    return {"exists": True}

# Endpoint for resetting a user's password
@app.post("/reset-password")
def reset_password_endpoint(
    request: ResetPasswordRequest, # The request body containing the username and new password
    db: sqlite3.Connection = Depends(get_db), # The database connection, injected by FastAPI's dependency system
):
    # Check if the username exists before attempting to reset the password
    if not username_exists(request.username):
        raise HTTPException(status_code=404, detail="Username not found")

    # Sets password_hash in user table to new password hash
    db.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (hash_password(request.new_password), request.username)
    )
    db.commit()
    return {"message": "Password reset successfully"}