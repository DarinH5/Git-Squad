"""Thin wrapper the Streamlit pages use to talk to the FastAPI backend (main.py)."""
import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def _request(method: str, path: str, token: str = None, **kwargs):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.request(
            method, f"{BACKEND_URL}{path}", headers=headers, timeout=25, **kwargs
        )
    except requests.RequestException:
        raise ApiError("Can't reach the backend. Start it with: uvicorn main:app --reload")
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        if isinstance(detail, list):  # request-validation errors
            detail = "; ".join(d.get("msg", "Invalid input") for d in detail)
        raise ApiError(detail or f"Request failed ({response.status_code})", response.status_code)
    return response.json()


# ---- session helpers -------------------------------------------------------
def set_session(data: dict):
    st.session_state.logged_in = True
    st.session_state.token = data["token"]
    st.session_state.username = data["username"]


def clear_session():
    st.session_state.logged_in = False
    st.session_state.token = None
    st.session_state.username = None


def logout_session():
    """Invalidate the token server-side (best effort), then clear local state."""
    try:
        if st.session_state.get("token"):
            _request("POST", "/auth/logout", st.session_state.token)
    except ApiError:
        pass
    clear_session()


# ---- endpoints -------------------------------------------------------------
def login(username: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"username": username, "password": password})


def signup(username: str, email: str, password: str) -> dict:
    return _request(
        "POST", "/auth/signup", json={"username": username, "email": email, "password": password}
    )


def recover(email: str) -> dict:
    return _request("POST", "/auth/recover", json={"email": email})


def reset_password(token: str, new_password: str) -> dict:
    return _request("POST", "/auth/reset", json={"token": token, "new_password": new_password})


def search_products(query: str, token: str, min_score: int = 0) -> dict:
    """Search products and return both ranked products and interpreted intent."""
    return _request(
        "GET",
        "/products/search",
        token,
        params={"q": query, "min_score": min_score},
    )
