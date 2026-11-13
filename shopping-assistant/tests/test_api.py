import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def isolated_app(tmp_path_factory):
    """
    Import the backend in a separate Python process.

    This ensures DB_PATH is set before backend.main calls init_db().
    The real shop.db is never used.
    """
    temp_dir = tmp_path_factory.mktemp("git_squad_api")
    db_path = temp_dir / "test_shop.db"

    env = os.environ.copy()
    env["DB_PATH"] = str(db_path)
    env["GEMINI_API_KEY"] = ""
    env["SECRET_KEY"] = "unit-test-secret-key-not-for-production"

    return env, db_path


def run_isolated(env, script):
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Subprocess failed:\n{result.stdout}\n{result.stderr}"
    )


def test_health_endpoint(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
response = client.get("/health")

assert response.status_code == 200
assert response.json() == {"status": "ok", "service": "shopwise-ai"}
""")


def test_account_creation(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
response = client.post(
    "/signup",
    json={"username": "test_signup", "password": "SecurePass123"}
)

assert response.status_code == 201
assert response.json()["message"] == "Account created"
assert "recovery_code" in response.json()
""")


def test_duplicate_username(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
data = {"username": "duplicate_user", "password": "SecurePass123"}

first = client.post("/signup", json=data)
second = client.post("/signup", json=data)

assert first.status_code == 201
assert second.status_code == 409
""")


def test_correct_login(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

client.post(
    "/signup",
    json={"username": "login_user", "password": "SecurePass123"}
)

response = client.post(
    "/login",
    data={"username": "login_user", "password": "SecurePass123"}
)

assert response.status_code == 200
assert "access_token" in response.json()
""")


def test_incorrect_password(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

client.post(
    "/signup",
    json={"username": "wrong_password_user", "password": "SecurePass123"}
)

response = client.post(
    "/login",
    data={"username": "wrong_password_user", "password": "WrongPassword"}
)

assert response.status_code == 401
""")


def test_unknown_username(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
response = client.post(
    "/login",
    data={"username": "does_not_exist", "password": "SecurePass123"}
)

assert response.status_code == 401
""")


def test_search_under_budget(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
import sqlite3
from backend.main import DB_PATH, search_products

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
result = search_products(db, q="boots under $100")

assert result["applied"]["max_price"] == 100.0
assert len(result["results"]) > 0
assert all(item["price"] <= 100 for item in result["results"])
assert all("boot" in item["title"].lower() for item in result["results"])
db.close()
""")


def test_explicit_price_override(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
import sqlite3
from backend.main import DB_PATH, search_products

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
result = search_products(
    db,
    q="boots under $100",
    max_price=150
)

assert result["applied"]["max_price"] == 150
assert any(item["price"] > 100 for item in result["results"])
db.close()
""")


def test_unknown_product_returns_empty(isolated_app):
    env, _ = isolated_app
    run_isolated(env, """
import sqlite3
from backend.main import DB_PATH, search_products

db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
result = search_products(db, q="nonexistentproductxyz")

assert result["results"] == []
db.close()
""")
