import pytest

from test_api import client, test_db


def authenticated_client(client):
    response = client.post(
        "/signup",
        json={
            "username": "profile_test_user",
            "password": "SecurePass123"
        }
    )
    assert response.status_code == 201

    login = client.post(
        "/login",
        data={
            "username": "profile_test_user",
            "password": "SecurePass123"
        }
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_profile_requires_authentication(client):
    response = client.get("/me/profile")

    assert response.status_code == 401


def test_update_profile_preferences(client):
    headers = authenticated_client(client)

    response = client.patch(
        "/me/profile",
        headers=headers,
        json={
            "display_name": "Test Shopper",
            "budget_min": 20,
            "budget_max": 150,
            "preferred_brands": ["TrailCo"],
            "preferred_categories": ["footwear"],
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Test Shopper"
    assert response.json()["budget_max"] == 150
    assert response.json()["preferred_brands"] == ["TrailCo"]


def test_invalid_budget_range(client):
    headers = authenticated_client(client)

    response = client.patch(
        "/me/profile",
        headers=headers,
        json={"budget_min": 200, "budget_max": 100},
    )

    assert response.status_code == 422


def test_duplicate_brands_are_removed(client):
    headers = authenticated_client(client)

    response = client.patch(
        "/me/profile",
        headers=headers,
        json={
            "preferred_brands": [
                "TrailCo",
                "trailco",
                " TrailCo "
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["preferred_brands"] == ["TrailCo"]
