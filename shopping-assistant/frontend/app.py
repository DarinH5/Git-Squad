"""
Entry point and router. Run from the frontend/ folder:  streamlit run app.py

Logged out -> login page (Log in / Sign up tabs) and recover page, no sidebar.
Logged in  -> sidebar navigation between the main pages.
"""
import streamlit as st
import api

st.set_page_config(page_title="Shopping Assistant", page_icon="🛍️", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Logged-out pages
login_page = st.Page("pages/login_page.py", title="Login", default=True)
recover_page = st.Page("pages/recover_page.py", title="Recover Password")

# Logged-in pages
home_page = st.Page("pages/home_page.py", title="Home", default=True)
products_page = st.Page("pages/products_page.py", title="Browse")
chatbot_page = st.Page("pages/chatbot_page.py", title="Chatbot")
projects_page = st.Page("pages/projects_page.py", title="Projects")
profile_page = st.Page("pages/profile_page.py", title="Profile")
faq_page = st.Page("pages/faq_page.py", title="FAQ")

if st.session_state.logged_in:
    pg = st.navigation({"Shop": [home_page, products_page, chatbot_page, projects_page], "Account": [profile_page, faq_page]})
    with st.sidebar:
        st.divider()
        st.write(f"Signed in as **{st.session_state.username}**")
        if st.button("Log out"):
            api.logout()
            st.rerun()
else:
    # Hide the sidebar and its toggle while logged out. Streamlit can leave the sidebar showing
    # after a logout, so this makes sure the login screen never has one.
    st.markdown(
        """<style>
            [data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="collapsedControl"] { display: none !important; }
        </style>""",
        unsafe_allow_html=True,
    )
    pg = st.navigation([login_page, recover_page], position="hidden")

pg.run()