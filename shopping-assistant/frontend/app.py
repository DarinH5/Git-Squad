"""
Entry point and router. Run from the frontend/ folder:  streamlit run app.py

Logged out -> login page (Log in / Sign up tabs) and recover page, no sidebar.
Logged in  -> sidebar navigation between the main pages.
"""

#Imports api from api.py to handle user login/logout functionality
import streamlit as st
import api

#UI stuff
st.set_page_config(page_title="Shopping Assistant", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Pages users can see when logged out
login_page = st.Page("pages/login_page.py", title="Login", default=True)
recover_page = st.Page("pages/recover_page.py", title="Recover Password")

# Pages users can see when logged in
# Should work on combining home page and chatbot page, chatbot should be first thing user sees?
home_page = st.Page("pages/home_page.py", title="Home", default=True)
chatbot_page = st.Page("pages/chatbot_page.py", title="Chatbot",)
profile_page = st.Page("pages/profile_page.py", title="Profile")
faq_page = st.Page("pages/faq_page.py", title="FAQ")
products_page = st.Page("pages/products_page.py", title="Browse")


#Creates the sidebar for navigation when user is logged in
if st.session_state.logged_in:
    pg = st.navigation({"Shop": [home_page, chatbot_page, products_page], "Account": [profile_page, faq_page]})
    with st.sidebar:
        st.divider()
        st.write(f"Signed in as **{st.session_state.username}**")
        if st.button("Log out", use_container_width=True):
            api.logout()
            st.rerun()
else:
    pg = st.navigation([login_page, recover_page], position="hidden")

pg.run()