#Need to make this work

import streamlit as st
def email_entered():
    email = st.session_state.email
    confirm_email = st.session_state.confirm_email

    if (email == confirm_email):
        st.success("Emails match!")
    else:
        st.error("Emails do not match!")
    #return st.text_input("Email/Username?", placeholder="example@example.com")

st.markdown("""
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
""", unsafe_allow_html=True)

email = st.text_input("Email/Username?", 
                        placeholder="example@example.com",
                        key="email")
confirm_email = st.text_input("Confirm Email/Username?", 
                                placeholder="example@example.com",
                                key="confirm_email",
                                on_change = email_entered)    

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Send Reset Link"):
        # Handle password reset logic here
        st.write("Reset link sent to your email.")
        pass
    if st.button("Back to Login"):
        st.session_state.page = "login_page"
        st.rerun()