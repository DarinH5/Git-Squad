import streamlit as st

import api
from components import show_recovery_code

st.title("Profile")
r = api.get("/me")
if r.ok:
    st.write(f"**Username:** {r.json()['username']}")
else:
    st.error("Couldn't load your profile.")

st.divider()
st.subheader("Change password")
with st.form("change_password", clear_on_submit=True):
    current = st.text_input("Current password", type="password")
    new_pw = st.text_input("New password (8+ characters)", type="password")
    confirm = st.text_input("Confirm new password", type="password")
    if st.form_submit_button("Change password"):
        if not (current and new_pw):
            st.error("Fill in every field.")
        elif new_pw != confirm:
            st.error("The two new passwords don't match.")
        else:
            ok, msg = api.change_password(current, new_pw)
            (st.success if ok else st.error)(msg)

st.divider()
st.subheader("Recovery code")
st.caption("The recovery code lets you reset your password if you forget it. "
           "Making a new one makes the old one stop working.")
if st.session_state.get("recovery_to_show"):
    if show_recovery_code(st.session_state.recovery_to_show, "dismiss_profile_code"):
        del st.session_state["recovery_to_show"]
        st.rerun()
else:
    with st.form("new_code_form", clear_on_submit=True):
        pw = st.text_input("Confirm your password", type="password")
        if st.form_submit_button("Generate new recovery code"):
            ok, result = api.new_recovery_code(pw)
            if ok:
                st.session_state.recovery_to_show = result
                st.rerun()
            else:
                st.error(result)