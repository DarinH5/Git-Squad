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
