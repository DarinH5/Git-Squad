"""All calls to the FastAPI backend live here so pages stay clean."""
import requests
import streamlit as st

API = "http://localhost:8000"


def signup(username, password):
    """Returns (ok, message)."""
    try:
        r = requests.post(f"{API}/signup", json={"username": username, "password": password}, timeout=10)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.status_code == 201:
        return True, "Account created! You can log in now."
    if r.status_code == 409:
        return False, "That username is taken"
    if r.status_code == 422:
        return False, "Username needs 3+ characters, password 8-72"
    return False, f"Signup failed ({r.status_code})"


def login(username, password):
    """Returns (ok, message). On success, sets the session state flags."""
    try:
        # Login uses form encoding (data=), not json=
        r = requests.post(f"{API}/login", data={"username": username, "password": password}, timeout=10)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.ok:
        st.session_state.token = r.json()["access_token"]
        st.session_state.username = username
        st.session_state.logged_in = True
        return True, ""
    return False, "Invalid username or password"

def check_username(username):
    try:
        r = requests.get(f"{API}/check-username/{username}", timeout=5)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.status_code == 404:
        return False, "Username not found"
    if r.ok:
        return True, "Username exists"
    return False, f"Check failed ({r.status_code})"

#I get reset failed 422 why?
# reset failed (500)
def reset_password(username, new_password):
    try:
        r = requests.post(f"{API}/reset-password", json={"username": username, "new_password": new_password}, timeout=10)
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.ok:
        return True, "Password reset successfully"
    return False, f"Reset failed ({r.status_code})"

def logout():
    for key in ("token", "username", "messages"):
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