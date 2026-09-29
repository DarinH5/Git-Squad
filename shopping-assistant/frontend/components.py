import streamlit as st



def settings_menu():
 import streamlit as st



def settings_menu():
    st.markdown("""
    <style>
        div[data-testid="stPopoverButton"] {
            position: fixed;
            top: 10px;
            right: 25px;
            z-index: 9999;
        }
    </style>
    """, unsafe_allow_html=True)

    if "theme" not in st.session_state:
        st.session_state.theme = "Light"
    with st.popover("⚙️"):
        if st.button("Change Theme"):
            st.write("Theme changed!")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        theme = st.selectbox(
            "Theme",
            ["Light", "Dark"],
            index=0 if st.session_state.theme == "Light" else 1
        )
        st.session_state.theme = theme
def apply_theme():
    if st.session_state.theme == "Dark":
        st.markdown("""
        <style>
            .stApp {
                background-color: #2e383d;
                color: white;
            }

            [data-testid="stSidebar"] {
                background-color: #1B262C;
            }

            h1, h2, h3, p, label {
                color: white !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .stApp {
                background-color: #ceedfd;
                color: #889297;
            }
            [data-testid="stSidebar"] {
                background-color: #9dd8f6;  
            }

            h1, h2, h3, p, label {
                color: #889297 !important;
            }
        </style>
        """, unsafe_allow_html=True)