"""All calls to the FastAPI backend live here so pages stay clean."""
import os
import requests
import streamlit as st

API = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def signup(username, password):
    """Returns (ok, message, recovery_code). The code is only returned on success."""
    try:
        r = requests.post(f"{API}/signup", json={"username": username, "password": password}, timeout=45)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?", None
    if r.status_code == 201:
        return True, "Account created!", r.json().get("recovery_code")
    if r.status_code == 409:
        return False, "That username is taken", None
    if r.status_code == 422:
        return False, "Username needs 3+ characters, password 8-72", None
    return False, f"Signup failed ({r.status_code})", None


def recover(username, recovery_code, new_password):
    """Reset a forgotten password. Returns (ok, message, new_recovery_code)."""
    try:
        r = requests.post(
            f"{API}/recover",
            json={"username": username, "recovery_code": recovery_code, "new_password": new_password},
            timeout=10,
        )
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?", None
    if r.ok:
        return True, "Password reset!", r.json()["recovery_code"]
    if r.status_code == 400:
        return False, "Invalid username or recovery code", None
    if r.status_code == 422:
        return False, "New password must be 8-72 characters", None
    return False, f"Reset failed ({r.status_code})", None


def login(username, password):
    """Returns (ok, message). On success, sets the session state flags."""
    try:
        # Login uses form encoding (data=), not json=
        r = requests.post(f"{API}/login", data={"username": username, "password": password}, timeout=45)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.ok:
        st.session_state.token = r.json()["access_token"]
        st.session_state.username = username
        st.session_state.logged_in = True
        return True, ""
    return False, "Invalid username or password"


def logout():
    for key in ("token", "username", "messages", "recovery_to_show", "open_project"):
        st.session_state.pop(key, None)
    st.session_state.logged_in = False


def _request(method, path, body=None, **params):
    """Authenticated request. Logs the user out if the token has expired."""
    r = requests.request(
        method,
        f"{API}{path}",
        params=params,
        json=body,
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        timeout=10,
    )
    if r.status_code == 401:
        logout()
        st.rerun()
    return r


def get(path, **params):
    return _request("GET", path, **params)


def post(path, body=None, **params):
    """body (optional) is sent as JSON; other keyword arguments go in the URL."""
    return _request("POST", path, body=body, **params)


def delete(path, **params):
    return _request("DELETE", path, **params)


def change_password(current_password, new_password):
    """Logged-in password change. Returns (ok, message)."""
    r = post("/me/password", body={"current_password": current_password, "new_password": new_password})
    if r.ok:
        return True, "Password changed!"
    if r.status_code == 400:
        return False, "Current password is incorrect"
    return False, "New password must be 8-72 characters" if r.status_code == 422 else f"Failed ({r.status_code})"


def new_recovery_code(password):
    """Make a fresh recovery code. Returns (ok, code_or_message)."""
    r = post("/me/recovery-code", body={"password": password})
    if r.ok:
        return True, r.json()["recovery_code"]
    return False, "Password is incorrect" if r.status_code == 400 else f"Failed ({r.status_code})"


def update_profile(**fields):
    """Update only the profile fields supplied by the caller."""
    return _request("PATCH", "/me/profile", body=fields)


def shop_with_agents(query, limit=12):
    """Run the embedded multi-agent shopping workflow."""
    return post("/agents/shop", body={"query": query, "limit": limit})


def get_profile():
    return get("/me/profile")
