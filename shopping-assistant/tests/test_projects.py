import pytest



@pytest.fixture
def users(client):
    """Create two independent users to test project ownership."""

    headers = {}

    for username in ("project_owner", "project_other"):
        signup = client.post(
            "/signup",
            json={
                "username": username,
                "password": "SecurePass123"
            }
        )
        assert signup.status_code == 201

        login = client.post(
            "/login",
            data={
                "username": username,
                "password": "SecurePass123"
            }
        )
        assert login.status_code == 200

        headers[username] = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }

    return headers


@pytest.fixture
def project(client, users):
    response = client.post(
        "/projects",
        headers=users["project_owner"],
        json={"name": "My Shopping List"}
    )

    assert response.status_code == 201
    return response.json()


@pytest.fixture
def product_id(db):
    row = db.execute(
        "SELECT id FROM products ORDER BY id LIMIT 1"
    ).fetchone()

    assert row is not None
    return row["id"]


def test_create_project(client, users):
    response = client.post(
        "/projects",
        headers=users["project_owner"],
        json={"name": "Gaming Setup"}
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Gaming Setup"
    assert isinstance(response.json()["id"], int)


def test_blank_project_name_rejected(client, users):
    response = client.post(
        "/projects",
        headers=users["project_owner"],
        json={"name": "   "}
    )

    assert response.status_code == 422


def test_list_projects(client, users, project):
    response = client.get(
        "/projects",
        headers=users["project_owner"]
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "My Shopping List"
    assert response.json()[0]["item_count"] == 0


def test_add_product_to_project(
    client, users, project, product_id
):
    response = client.post(
        f"/projects/{project['id']}/items",
        headers=users["project_owner"],
        params={"product_id": product_id}
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Added"

    listing = client.get(
        f"/projects/{project['id']}/items",
        headers=users["project_owner"]
    )

    assert listing.status_code == 200
    assert len(listing.json()["results"]) == 1
    assert listing.json()["results"][0]["id"] == product_id


def test_duplicate_product_not_added_twice(
    client, users, project, product_id
):
    url = f"/projects/{project['id']}/items"
    params = {"product_id": product_id}

    first = client.post(
        url, headers=users["project_owner"], params=params
    )
    second = client.post(
        url, headers=users["project_owner"], params=params
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["message"] == "Already in project"

    listing = client.get(
        url, headers=users["project_owner"]
    )
    assert len(listing.json()["results"]) == 1


def test_invalid_product_rejected(client, users, project):
    response = client.post(
        f"/projects/{project['id']}/items",
        headers=users["project_owner"],
        params={"product_id": -999}
    )

    assert response.status_code == 404


def test_remove_product(client, users, project, product_id):
    client.post(
        f"/projects/{project['id']}/items",
        headers=users["project_owner"],
        params={"product_id": product_id}
    )

    response = client.delete(
        f"/projects/{project['id']}/items/{product_id}",
        headers=users["project_owner"]
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Removed"

    listing = client.get(
        f"/projects/{project['id']}/items",
        headers=users["project_owner"]
    )
    assert listing.json()["results"] == []


def test_delete_project(client, users, project):
    response = client.delete(
        f"/projects/{project['id']}",
        headers=users["project_owner"]
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Project deleted"

    listing = client.get(
        "/projects",
        headers=users["project_owner"]
    )
    assert listing.json() == []


def test_other_user_cannot_view_project(
    client, users, project
):
    response = client.get(
        f"/projects/{project['id']}/items",
        headers=users["project_other"]
    )

    assert response.status_code == 404


def test_other_user_cannot_add_items(
    client, users, project, product_id
):
    response = client.post(
        f"/projects/{project['id']}/items",
        headers=users["project_other"],
        params={"product_id": product_id}
    )

    assert response.status_code == 404


def test_other_user_cannot_delete_project(
    client, users, project
):
    response = client.delete(
        f"/projects/{project['id']}",
        headers=users["project_other"]
    )

    assert response.status_code == 404

    owner_listing = client.get(
        "/projects",
        headers=users["project_owner"]
    )
    assert len(owner_listing.json()) == 1


def test_other_user_cannot_remove_items(
    client, users, project, product_id
):
    response = client.delete(
        f"/projects/{project['id']}/items/{product_id}",
        headers=users["project_other"]
    )

    assert response.status_code == 404


def test_projects_require_authentication(client):
    assert client.get("/projects").status_code == 401

    assert client.post(
        "/projects",
        json={"name": "Unauthorized"}
    ).status_code == 401
