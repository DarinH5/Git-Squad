"""Streamlit entry point for the AI Shopping Assistant."""
import streamlit as st
import api
from components import apply_theme

st.set_page_config(page_title="Shopwise AI", page_icon="🛍️", layout="wide",
                   initial_sidebar_state="expanded")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

login_page = st.Page("pages/login_page.py", title="Sign in", icon=":material/login:", default=True)
recover_page = st.Page("pages/recover_page.py", title="Recover account", icon=":material/lock_reset:")
home_page = st.Page("pages/home_page.py", title="AI Shopping", icon=":material/auto_awesome:", default=True)
products_page = st.Page("pages/products_page.py", title="Explore", icon=":material/storefront:")
chatbot_page = st.Page("pages/chatbot_page.py", title="Web search", icon=":material/travel_explore:")
projects_page = st.Page("pages/projects_page.py", title="Collections", icon=":material/bookmarks:")
profile_page = st.Page("pages/profile_page.py", title="My profile", icon=":material/person:")
faq_page = st.Page("pages/faq_page.py", title="Help", icon=":material/help_outline:")

if st.session_state.logged_in:
    with st.sidebar:
        st.markdown("## 🛍️ Shopwise AI")
        st.caption("Personal shopping, powered by agents")
        st.divider()
        st.write(f"Signed in as **{st.session_state.username}**")
        if st.button("Log out", use_container_width=True):
            api.logout()
            st.rerun()
        st.caption("Backend API · [Interactive docs](http://127.0.0.1:8000/docs)")
    pg = st.navigation({
        "SHOP": [home_page, products_page, chatbot_page, projects_page],
        "ACCOUNT": [profile_page, faq_page],
    })
else:
    st.markdown("""<style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] { display: none !important; }
    </style>""", unsafe_allow_html=True)
    pg = st.navigation([login_page, recover_page], position="hidden")

apply_theme()
pg.run()
