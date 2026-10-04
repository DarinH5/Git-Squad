import streamlit as st

import api_client as api

st.markdown(
    """
    <style>
        .signup_title {
            text-align: center;
            font-size: 4rem !important;
        }
    div[data-testid="stTextInput"] label{
        display: block !important;
        text-align: center !important;
    }

    div[data-testid="stTextInput"] input {
        text-align: center !important;
    }
    </style>

<h1 class = "signup_title">
    Sign Up
</h1>
""",
    unsafe_allow_html=True,
)

username = st.text_input("Username", placeholder="3-30 letters, numbers, . _ -", key="su_username")
email = st.text_input("Email", placeholder="example@example.com", key="su_email")
password = st.text_input("Password", type="password", placeholder="At least 8 characters", key="su_password")
confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="su_confirm")

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Create Account"):
        if not (username and email and password):
            st.error("Please fill in every field.")
        elif password != confirm_password:
            st.error("Passwords do not match!")
        else:
            try:
                api.set_session(api.signup(username, email, password))
                st.rerun()  # app.py now shows the logged-in navigation
            except api.ApiError as err:
                st.error(str(err))
    if st.button("Back to Login"):
        st.switch_page(st.session_state.pages["login"])
