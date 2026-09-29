import streamlit as st;

st.markdown("""
    <style>
        .faq_title {
            text-align: center;
            font-size: 3rem !important;
        }
    div[data-testid="stTextInput"] label{
        display: block !important;
        text-align: center !important;
    }

    div[data-testid="stTextInput"] input {
        text-align: center !important;
    }
    </style>

<h1 class = "faq_title">
    Frequently Asked Questions
</h1>
""", unsafe_allow_html=True)

st.markdown("---")
st.text("Q1: How do I reset my password?")
st.text("A1: You can reset your password by clicking on the 'Forgot Password' link on the login page.")
st.markdown("---")
st.markdown("Q2: blah blah blah")
st.markdown("A2: blah blah blah")
st.markdown("---")
