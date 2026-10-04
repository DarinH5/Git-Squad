# Entry point: run with `streamlit run app.py` (backend must be running: uvicorn main:app --reload)
import streamlit as st

import api_client as api
from components import apply_theme

if "logged_in" not in st.session_state:
    api.clear_session()


def login():
    st.markdown(
        """
        <style>
            .login_title {
                text-align: center;
                font-size: 7rem !important;
            }

            div[data-testid="stTextInput"] label{
                display: block !important;
                text-align: center !important;
            }
        </style>
    <h1 class = "login_title">
        Login
    </h1>
    """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        username = st.text_input("Username or email")
        password = st.text_input("Password", type="password")
        if st.button("Press to Login"):
            try:
                api.set_session(api.login(username, password))
                st.rerun()
            except api.ApiError as err:
                st.error(str(err))
        if st.button("Forgot Password?"):
            st.switch_page(st.session_state.pages["recover"])
        if st.button("Don't have an account? Sign up here"):
            st.switch_page(st.session_state.pages["signup"])


def logout():
    api.logout_session()
    st.rerun()


login_page = st.Page(login, title="Login")
logout_page = st.Page(logout, title="Logout")
recover_page = st.Page("pages/recover_page.py", title="Recover Password")
home_page = st.Page("pages/home_page.py", title="Home", default=True)
project_page = st.Page("pages/projects_page.py", title="Project")
profile = st.Page("pages/profile_page.py", title="Profile")
faq_page = st.Page("pages/faq_page.py", title="FAQ")
signup_page = st.Page("pages/signup_page.py", title="Sign Up")
chatbot_page = st.Page("pages/chatbot_page.py", title="Chatbot")

# Pages use these for st.switch_page (replaces `from app import login_page`,
# which re-ran app.py and created a circular import).
st.session_state.pages = {"login": login_page, "recover": recover_page, "signup": signup_page}

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Account": [profile, logout_page],
            "Home": [home_page, project_page],
            "Help": [faq_page],
            "Chatbot": [chatbot_page],
        }
    )
else:
    pg = st.navigation([login_page, recover_page, signup_page])

apply_theme()  # themes every page, including login/signup/recover
pg.run()
