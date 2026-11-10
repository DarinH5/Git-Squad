import streamlit as st

import api
from components import show_recovery_code

st.markdown("<div style='text-align:center;padding:3rem 0 1rem;'>"
            "<div style='font-size:3rem;'>🛍️</div>"
            "<h1 style='font-size:2.6rem;margin-bottom:0;'>Shopwise AI</h1>"
            "<p style='color:var(--text-color);opacity:.7;'>Smarter product discovery, tailored to you.</p>"
            "</div>", unsafe_allow_html=True)

_, center, _ = st.columns([1, 1.4, 1])
with center:
    with st.container(border=True):
        login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
        with login_tab:
            username = st.text_input("Username", key="li_user")
            password = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign in", type="primary", use_container_width=True):
                ok, msg = api.login(username, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)
            if st.button("Forgot password?", use_container_width=True):
                st.switch_page("pages/recover_page.py")

        with signup_tab:
            if st.session_state.get("recovery_to_show"):
                st.success("Your account was created. Save this recovery code before signing in.")
                if show_recovery_code(st.session_state.recovery_to_show, "dismiss_signup_code"):
                    del st.session_state["recovery_to_show"]
                    st.rerun()
            else:
                new_user = st.text_input("Choose a username", key="su_user")
                new_pw = st.text_input("Choose a password (8+ characters)", type="password", key="su_pw")
                if st.button("Create account", type="primary", use_container_width=True):
                    ok, msg, code = api.signup(new_user, new_pw)
                    if ok:
                        st.session_state.recovery_to_show = code
                        st.rerun()
                    else:
                        st.error(msg)
