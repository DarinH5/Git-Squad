import streamlit as st

import api
from components import show_recovery_code

st.title("Recover Password")

# After a successful reset, show the new recovery code until the user confirms
if st.session_state.get("recovery_to_show"):
    st.success("Your password was reset. You can log in with the new password.")
    if show_recovery_code(st.session_state.recovery_to_show, "dismiss_reset_code"):
        del st.session_state["recovery_to_show"]
        st.switch_page("pages/login_page.py")
else:
    st.write("Enter your username and the recovery code you were given when you created your account.")
    with st.form("recover_form"):
        username = st.text_input("Username", key="rec_user")
        code = st.text_input("Recovery code", key="rec_code", placeholder="XXXX-XXXX-XXXX-XXXX")
        new_pw = st.text_input("New password (8+ characters)", type="password", key="rec_pw")
        confirm = st.text_input("Confirm new password", type="password", key="rec_pw2")
        submitted = st.form_submit_button("Reset password")

    if submitted:
        if not (username and code and new_pw):
            st.error("Fill in every field.")
        elif new_pw != confirm:
            st.error("The two passwords don't match.")
        else:
            ok, msg, new_code = api.recover(username, code, new_pw)
            if ok:
                st.session_state.recovery_to_show = new_code
                st.rerun()
            else:
                st.error(msg)

    st.caption("Lost your recovery code too? Without email, there's no way to verify it's you, "
               "so you'd need to create a new account.")

if st.button("Back to login"):
    st.session_state.pop("recovery_to_show", None)
    st.switch_page("pages/login_page.py")