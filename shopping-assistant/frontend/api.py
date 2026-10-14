"""All calls to the FastAPI backend live here so pages stay clean."""
import requests
import streamlit as st


API = "http://localhost:8000"


def signup(username, password):
    # Create an account and return a UI-friendly success or error message.
    """Returns (ok, message)."""
    try:
        r = requests.post(
            f"{API}/signup",
            json={"username": username, "password": password},
            timeout=10,
        )
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
    # Authenticate the user and load their saved profile preferences.
    """Returns (ok, message). On success, sets the session state flags."""
    try:
        r = requests.post(
            f"{API}/login",
            data={"username": username, "password": password},
            timeout=10,
        )
    except requests.ConnectionError:
        return False, "Can't reach the backend. Is uvicorn running?"
    if r.ok:
        st.session_state.token = r.json()["access_token"]
        st.session_state.username = username
        st.session_state.logged_in = True
        profile = get("/me")
        if profile.ok:
            data = profile.json()
            st.session_state.app_theme = data.get("theme", "Dark")
            st.session_state.saved_theme = st.session_state.app_theme
            st.session_state.bio = data.get("bio", "")
            st.session_state.profile_bio_loaded = True
        return True, ""
    return False, "Invalid username or password"


def logout():
    # Clear local account and profile state without deleting persisted data.
    """Clear local session state without changing persisted profile data."""
    for key in ("token", "username", "messages", "bio", "saved_theme", "profile_bio_loaded"):
        st.session_state.pop(key, None)
    st.session_state.app_theme = "Dark"
    st.session_state.pop("theme_selector", None)
    st.session_state.logged_in = False


def get(path, **params):
    # Make an authenticated GET request and handle expired sessions.
    """Authenticated GET. Logs the user out if the token has expired."""
    r = requests.get(
        f"{API}{path}",
        params=params,
        headers={"Authorization": "Bearer " + st.session_state.get("token", "")},
        timeout=10,
    )
    if r.status_code == 401:
        logout()
        st.rerun()
    return r


def update_profile(**changes):
    """Persist profile changes for the currently authenticated user."""
    r = requests.put(
        f"{API}/profile",
        json=changes,
        headers={"Authorization": "Bearer " + st.session_state.get("token", "")},
        timeout=10,
    )
    if r.status_code == 401:
        logout()
        st.rerun()
    return r
