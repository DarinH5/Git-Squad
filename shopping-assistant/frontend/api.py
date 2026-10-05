"""All calls to the FastAPI backend live here so pages stay clean."""
import requests
import streamlit as st


#This is the backends base address, changes when you move from page
#Example, if we go to signup page, this becomes "http://localhost:8000/signup"
#This is used later in code by f"{API}/some_endpoint"
API = "http://localhost:8000"


#Sign up logic
#User input is turned into json for backend to process using requests.post()
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

#Login logic
#   Essentially the same as signup, but uses the from data instead of json, this is because 
#   the backend expects form-encoded data for login.
#   If user login is valid, the backend generates a token for the session
#   which is then stored in the session state for subsequent authenticated requests.

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

#logout logic
#   Clears the session state flags to log the user out.
def logout():
    for key in ("token", "username", "messages"):
        st.session_state.pop(key, None)
    st.session_state.logged_in = False

# This function performs an authenticated GET request to the backend.
# We need this because this function builds the url with the API base and appends the path and query parameters.
# Params can be used later for adding search query requests to url for backend to process
# headers proves the user's authentication to the backend.
# This logs the user out if the token has expired. 
def get(path, **params):
    """Authenticated GET. Logs the user out if the token has expired."""
    r = requests.get(
        f"{API}{path}",
        params=params,
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        timeout=10,
    )
    if r.status_code == 401:
        logout()
        st.rerun()
    return r