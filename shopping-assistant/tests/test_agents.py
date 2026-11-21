import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from backend import main


@pytest.fixture
def auth_headers(client):
    signup = client.post(
        "/signup",
        json={
            "username": "agent_test_user",
            "password": "SecurePass123"
        }
    )
    assert signup.status_code == 201

    login = client.post(
        "/login",
        data={
            "username": "agent_test_user",
            "password": "SecurePass123"
        }
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def test_agent_without_gemini(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main, "gemini_client", None)

    response = client.post(
        "/agents/shop",
        headers=auth_headers,
        json={"query": "boots under $100"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["applied"]["max_price"] == 100
    assert len(data["agents"]) == 4
    assert len(data["results"]) > 0


def test_agent_respects_query_budget(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main, "gemini_client", None)

    response = client.post(
        "/agents/shop",
        headers=auth_headers,
        json={"query": "boots under $100"}
    )

    assert response.status_code == 200
    assert all(
        item["price"] <= 100
        for item in response.json()["results"]
    )


def test_agent_respects_saved_budget(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main, "gemini_client", None)

    profile = client.patch(
        "/me/profile",
        headers=auth_headers,
        json={"budget_max": 80}
    )
    assert profile.status_code == 200

    response = client.post(
        "/agents/shop",
        headers=auth_headers,
        json={"query": "boots"}
    )

    assert response.status_code == 200
    assert response.json()["personalized"] is True
    assert response.json()["applied"]["max_price"] == 80
    assert all(
        item["price"] <= 80
        for item in response.json()["results"]
    )


def test_agent_applies_preferred_brand(client, auth_headers, monkeypatch):
    monkeypatch.setattr(main, "gemini_client", None)

    profile = client.patch(
        "/me/profile",
        headers=auth_headers,
        json={"preferred_brands": ["TrailCo"]}
    )
    assert profile.status_code == 200

    response = client.post(
        "/agents/shop",
        headers=auth_headers,
        json={"query": "boots"}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["brand"] == "TrailCo"
    assert results[0]["personalization_score"] >= 15


def test_agent_requires_authentication(client):
    response = client.post(
        "/agents/shop",
        json={"query": "boots"}
    )

    assert response.status_code == 401


def test_agent_falls_back_when_gemini_fails(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(main, "gemini_client", object())

    def unavailable(query, categories):
        raise HTTPException(status_code=503, detail="Unavailable")

    monkeypatch.setattr(
        main, "interpret_search_query", unavailable
    )

    response = client.post(
        "/agents/shop",
        headers=auth_headers,
        json={"query": "boots under $100"}
    )

    assert response.status_code == 200
    assert response.json()["applied"]["max_price"] == 100
    assert "built-in" in response.json()["interpretation"]


def test_ai_search_with_mocked_gemini(
    client, auth_headers, monkeypatch
):
    def fake_interpretation(query, categories):
        return {
            "keywords": "boots",
            "min_price": None,
            "max_price": 100,
            "category": "footwear",
            "explanation": "Looking for affordable boots"
        }

    monkeypatch.setattr(
        main, "interpret_search_query", fake_interpretation
    )

    response = client.post(
        "/ai-search",
        headers=auth_headers,
        json={"query": "boots under $100"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["applied"]["max_price"] == 100
    assert data["applied"]["category"] == "footwear"
    assert len(data["results"]) > 0


def test_invalid_gemini_json(monkeypatch):
    """Malformed Gemini JSON must trigger local interpretation."""
    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs:
                SimpleNamespace(text="not valid json")
        )
    )
    monkeypatch.setattr(main, "gemini_client", fake_client)

    result = main.interpret_search_query(
        "boots under $100", ["footwear"]
    )

    assert isinstance(result, dict)
    assert result["max_price"] == 100
    assert isinstance(result["keywords"], str)
    assert result["keywords"].strip()



def test_ai_search_rejects_invalid_prices(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        main,
        "interpret_search_query",
        lambda query, categories: {
            "keywords": "boots",
            "min_price": 200,
            "max_price": 100,
            "category": "footwear",
            "explanation": "Invalid range"
        }
    )

    response = client.post(
        "/ai-search",
        headers=auth_headers,
        json={"query": "boots"}
    )

    assert response.status_code == 502


def test_ai_search_without_gemini(
    client, auth_headers, monkeypatch
):
    """AI search must work without the external Gemini service."""
    monkeypatch.setattr(main, "gemini_client", None)

    response = client.post(
        "/ai-search",
        headers=auth_headers,
        json={"query": "boots under $100"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["applied"]["max_price"] == 100
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0
    assert all(
        item["price"] <= 100
        for item in data["results"]
    )
