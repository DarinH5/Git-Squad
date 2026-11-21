"""Integration tests for account security endpoints."""

def signup(client, username="security_user", password="OriginalPass123"):
    response = client.post(
        "/signup",
        json={"username": username, "password": password},
    )
    assert response.status_code == 201
    return response.json()["recovery_code"]


def login(client, username="security_user", password="OriginalPass123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
    )


def auth_headers(client):
    response = login(client)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_change_password_success(client):
    signup(client)
    headers = auth_headers(client)

    response = client.post(
        "/me/password",
        headers=headers,
        json={
            "current_password": "OriginalPass123",
            "new_password": "UpdatedPass456",
        },
    )

    assert response.status_code == 200
    assert login(client).status_code == 401
    assert login(client, password="UpdatedPass456").status_code == 200


def test_change_password_rejects_wrong_current_password(client):
    signup(client)
    headers = auth_headers(client)

    response = client.post(
        "/me/password",
        headers=headers,
        json={
            "current_password": "IncorrectPass",
            "new_password": "UpdatedPass456",
        },
    )

    assert response.status_code == 400
    assert login(client).status_code == 200


def test_change_password_requires_authentication(client):
    signup(client)

    response = client.post(
        "/me/password",
        json={
            "current_password": "OriginalPass123",
            "new_password": "UpdatedPass456",
        },
    )

    assert response.status_code == 401


def test_regenerate_recovery_code_invalidates_old_code(client):
    original_code = signup(client)
    headers = auth_headers(client)

    response = client.post(
        "/me/recovery-code",
        headers=headers,
        json={"password": "OriginalPass123"},
    )

    assert response.status_code == 200
    new_code = response.json()["recovery_code"]
    assert new_code != original_code

    old_code_response = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "UpdatedPass456",
        },
    )

    assert old_code_response.status_code == 400
    assert login(client).status_code == 200


def test_recover_password_success_and_single_use_code(client):
    original_code = signup(client)

    response = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "UpdatedPass456",
        },
    )

    assert response.status_code == 200
    assert "recovery_code" in response.json()
    assert login(client).status_code == 401
    assert login(client, password="UpdatedPass456").status_code == 200

    reuse = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "AnotherPass789",
        },
    )

    assert reuse.status_code == 400
    assert login(client, password="UpdatedPass456").status_code == 200


def test_recover_rejects_invalid_username_or_code(client):
    signup(client)

    for username, code in [
        ("security_user", "WRONG-CODE"),
        ("unknown_user", "WRONG-CODE"),
    ]:
        response = client.post(
            "/recover",
            json={
                "username": username,
                "recovery_code": code,
                "new_password": "UpdatedPass456",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid username or recovery code"

    assert login(client).status_code == 200


def test_invalid_authentication_token(client):
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_expired_authentication_token(client):
    import datetime as dt
    import jwt
    from backend import main

    signup(client)

    expired_token = jwt.encode(
        {
            "sub": "security_user",
            "exp": dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(minutes=5),
        },
        main.SECRET_KEY,
        algorithm=main.ALGORITHM,
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_regenerate_recovery_code_rejects_wrong_password(client):
    original_code = signup(client)
    headers = auth_headers(client)

    response = client.post(
        "/me/recovery-code",
        headers=headers,
        json={"password": "WrongPassword123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Password is incorrect"

    # A failed regeneration must not invalidate the original code.
    recovery = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "UpdatedPass456",
        },
    )

    assert recovery.status_code == 200


def test_regenerate_recovery_code_requires_authentication(client):
    signup(client)

    response = client.post(
        "/me/recovery-code",
        json={"password": "OriginalPass123"},
    )

    assert response.status_code == 401


def test_recover_rejects_password_over_72_bytes(client):
    original_code = signup(client)

    response = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "😀" * 19,
        },
    )

    assert response.status_code == 422

    # Rejected requests must leave the original password unchanged.
    assert login(client).status_code == 200

    # The recovery code must remain valid.
    recovery = client.post(
        "/recover",
        json={
            "username": "security_user",
            "recovery_code": original_code,
            "new_password": "UpdatedPass456",
        },
    )

    assert recovery.status_code == 200
