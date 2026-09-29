import streamlit as st
from app import login_page

def password_entered():
    password = st.session_state.password
    c = st.session_state.confirm_password

    if (password == c):
        st.success("Passwords match!")
    else:
        st.error("Passwords do not match!")

st.markdown("""
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
""", unsafe_allow_html=True)

email = st.text_input("Email/Username?", 
                        placeholder="example@example.com",
                        key="email")
password = st.text_input("Password?", 
                            placeholder="Enter your password",
                            key="password")
confirm_password = st.text_input("Confirm Password?", 
                                    placeholder="Confirm your password",
                                    key="confirm_password",
                                    on_change = password_entered)    

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Send Reset Link"):
        # Handle password reset logic here
        st.write("Reset link sent to your email.")
        pass
    if st.button("Back to Login"):
        st.switch_page(login_page)