import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import main


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
