#Login Page Maybe might need this later when login is more complex
import streamlit as st

import api

st.markdown("""
    <style>
        .login_title {
            text-align: center;
            font-size: 7rem !important;
        }
        div[data-testid="stTextInput"] label {
            display: block !important;
            text-align: center !important;
        }
    </style>
    <h1 class="login_title">Welcome</h1>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="li_user")
            password = st.text_input("Password", type="password", key="li_pw")
            submitted = st.form_submit_button("Press to Login")
        if submitted:
            ok, msg = api.login(username, password)
            if ok:
                st.rerun()  # app.py reruns and now shows the sidebar navigation
            else:
                st.error(msg)  # no rerun here, or the message would vanish
        if st.button("Forgot Password?"):
            st.switch_page("pages/recover_page.py")

    with signup_tab:
        with st.form("signup_form"):
            new_user = st.text_input("Choose a username", key="su_user")
            new_pw = st.text_input("Choose a password (8+ characters)", type="password", key="su_pw")
            confirm_pw = st.text_input("Confirm password", type="password", key="su_confirm_pw")
            submitted = st.form_submit_button("Create account")
        if submitted:
            if new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                ok, msg = api.signup(new_user, new_pw)
                if ok:
                    st.success("Account created! Now log in from the other tab.")
                else:
                    st.error(msg)
