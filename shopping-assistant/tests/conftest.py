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

    # Apply the project-sharing schema to this isolated test database.
    main.sharing.init_tables(str(db_path))

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
