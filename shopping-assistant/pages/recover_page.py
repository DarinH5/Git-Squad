import streamlit as st

import api_client as api

st.markdown(
    """
    <style>
        .recover_title {
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

<h1 class = "recover_title">
    Recover Password
</h1>
""",
    unsafe_allow_html=True,
)

st.subheader("1. Request a reset link")
email = st.text_input("Email", placeholder="example@example.com", key="rec_email")
confirm_email = st.text_input("Confirm Email", placeholder="example@example.com", key="rec_confirm_email")

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Send Reset Link"):
        if not email:
            st.error("Please enter your email.")
        elif email.strip().lower() != confirm_email.strip().lower():
            st.error("Emails do not match!")
        else:
            try:
                result = api.recover(email)
                st.success(result["message"])
                # Only present when the backend runs with DEV_MODE=1 (no email service yet).
                if result.get("reset_token"):
                    st.info(f"Dev mode: your reset token is `{result['reset_token']}`")
            except api.ApiError as err:
                st.error(str(err))

st.markdown("---")
st.subheader("2. Set a new password")
token = st.text_input("Reset token", key="rec_token")
new_password = st.text_input("New password", type="password", placeholder="At least 8 characters", key="rec_new_pw")
confirm_new_password = st.text_input("Confirm new password", type="password", key="rec_confirm_pw")

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Reset Password"):
        if not token or not new_password:
            st.error("Enter your reset token and a new password.")
        elif new_password != confirm_new_password:
            st.error("Passwords do not match!")
        else:
            try:
                st.success(api.reset_password(token, new_password)["message"])
            except api.ApiError as err:
                st.error(str(err))
    if st.button("Back to Login"):
        st.switch_page(st.session_state.pages["login"])
