import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a completely separate database for each test."""

    db_path = tmp_path / "test_shop.db"

    # Redirect the application's database path.
    monkeypatch.setattr(main, "DB_PATH", str(db_path))

    # Initialize the test database using the real schema.
    main.init_db()

    yield db_path


@pytest.fixture
def client(test_db):
    """Create a FastAPI client with an isolated database."""

    def override_get_db():
        conn = sqlite3.connect(
            str(test_db),
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row

        try:
            yield conn
        finally:
            conn.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()


@pytest.fixture
def db(test_db):
    """Provide a database connection for search unit tests."""

    conn = sqlite3.connect(str(test_db))
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "shopwise-ai"
    }


def test_account_creation(client):
    response = client.post(
        "/signup",
        json={
            "username": "test_signup",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Account created"
    assert "recovery_code" in response.json()


def test_duplicate_username(client):
    data = {
        "username": "duplicate_user",
        "password": "SecurePass123"
    }

    first = client.post("/signup", json=data)
    second = client.post("/signup", json=data)

    assert first.status_code == 201
    assert second.status_code == 409


def test_correct_login(client):
    client.post(
        "/signup",
        json={
            "username": "login_user",
            "password": "SecurePass123"
        }
    )

    response = client.post(
        "/login",
        data={
            "username": "login_user",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_incorrect_password(client):
    client.post(
        "/signup",
        json={
            "username": "wrong_password_user",
            "password": "SecurePass123"
        }
    )

    response = client.post(
        "/login",
        data={
            "username": "wrong_password_user",
            "password": "WrongPassword"
        }
    )

    assert response.status_code == 401


def test_unknown_username(client):
    response = client.post(
        "/login",
        data={
            "username": "does_not_exist",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 401


def test_search_under_budget(db):
    result = main.search_products(
        db,
        q="boots under $100"
    )

    assert result["applied"]["max_price"] == 100.0
    assert len(result["results"]) > 0
    assert all(
        item["price"] <= 100
        for item in result["results"]
    )


def test_explicit_price_override(db):
    result = main.search_products(
        db,
        q="boots under $100",
        max_price=150
    )

    assert result["applied"]["max_price"] == 150
    assert any(
        item["price"] > 100
        for item in result["results"]
    )


def test_unknown_product_returns_empty(db):
    result = main.search_products(
        db,
        q="nonexistentproductxyz"
    )

    assert result["results"] == []
