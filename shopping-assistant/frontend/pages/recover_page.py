#Need to make this work

import streamlit as st
import requests
import api

# Sets page to confirm recovery username automatically
if "recovery_username" not in st.session_state:
    st.session_state.recovery_username = None



def show_recover_page():
    st.title("Confirm Username")
    username = st.text_input(
        "Username?",
        placeholder="your_username",
        key="recover_username"
    )

    confirm_username = st.text_input(
        "Confirm username",
        placeholder="your_username",
        key="confirm_recover_username"
    )
    if st.button("Continue"):
        if not username or not confirm_username:
            st.error("Please fill in both fields.")

        elif username != confirm_username:
            st.error("Usernames do not match.")

        else:
            try:
                response = api.check_username(username)

                if not response[0]:
                    st.error(response[1])

                else:
                    st.session_state.recovery_username = username
                    st.success("Username verified!")
                    st.rerun()
            except requests.RequestException:
                st.error("Could not connect to the backend.")
    if st.button("Back to Login"):
        st.switch_page("pages/login_page.py")
        st.rerun()

#I get reset failed 422 why?
def reset_password(username):
    st.title("Reset Password")
    new_password = st.text_input(
        "New Password",
        type="password",
        key="new_password"
    )
    confirm_password = st.text_input(
        "Confirm New Password",
        type="password",
        key="confirm_new_password"
    )
    if st.button("Reset Password"):
        if not new_password or not confirm_password:
            st.error("Please fill in both fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                response = api.reset_password(username, new_password)
                if not response[0]:
                    st.error(response[1])
                else:
                    st.success("Password reset successfully!")
                    st.session_state.recovery_username = None
                    st.switch_page("pages/login_page.py")
                    st.rerun()
            except requests.RequestException:
                st.error("Could not connect to the backend.")
    if st.button("Back to Login"):
        st.switch_page("pages/login_page.py")
        st.rerun()

# Determines what page to show
if st.session_state.recovery_username is None:
    show_recover_page()
else:
    reset_password(st.session_state.recovery_username)