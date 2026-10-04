import streamlit as st

import api_client as api

# Theme options shown in the settings menu. "UT Knoxville" = Tennessee Orange,
# White and Smokey Grey.
THEMES = ["Light", "Dark", "UT Knoxville"]

UT_ORANGE = "#FF8200"
UT_ORANGE_DARK = "#E57400"
UT_GREY = "#58595B"
UT_LIGHT_GREY = "#F2F2F2"
UT_BORDER_GREY = "#BCBEC0"

DARK_CSS = """
<style>
    .stApp { background-color: #2e383d; color: white; }
    [data-testid="stSidebar"] { background-color: #1B262C; }
    h1, h2, h3, p, label { color: white !important; }
</style>
"""

LIGHT_CSS = """
<style>
    .stApp { background-color: #ceedfd; color: #889297; }
    [data-testid="stSidebar"] { background-color: #9dd8f6; }
    h1, h2, h3, p, label { color: #889297 !important; }
</style>
"""

UT_CSS = f"""
<style>
    /* Page + sidebar */
    .stApp, [data-testid="stHeader"] {{ background-color: #FFFFFF; color: {UT_GREY}; }}
    [data-testid="stSidebar"] {{ background-color: {UT_ORANGE}; }}

    /* Text */
    h1, h2, h3 {{ color: {UT_ORANGE} !important; }}
    .stApp p, .stApp label, .stApp li, .stApp span,
    [data-testid="stCaptionContainer"] {{ color: {UT_GREY} !important; }}
    a {{ color: {UT_ORANGE} !important; }}
    hr {{ border-color: {UT_BORDER_GREY} !important; }}

    /* Sidebar text must be white on orange (placed after the generic text rule) */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] a, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li {{ color: #FFFFFF !important; }}

    /* Buttons */
    .stButton > button, [data-testid="stFormSubmitButton"] > button {{
        background-color: {UT_ORANGE}; border: 1px solid {UT_ORANGE}; color: #FFFFFF;
    }}
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: {UT_ORANGE_DARK}; border-color: {UT_ORANGE_DARK};
    }}
    .stButton > button p, .stButton > button span {{ color: #FFFFFF !important; }}

    /* Inputs (config.toml uses a dark base, so force light fields) */
    [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"],
    [data-baseweb="select"] > div, [data-testid="stChatInput"] > div {{
        background-color: #FFFFFF !important; border-color: {UT_BORDER_GREY} !important;
    }}
    input, textarea {{ background-color: #FFFFFF !important; color: {UT_GREY} !important; }}
    [data-baseweb="select"] span {{ color: {UT_GREY} !important; }}
    [data-baseweb="popover"] ul, [data-testid="stPopoverBody"] {{ background-color: #FFFFFF !important; }}
    [data-baseweb="popover"] li {{ color: {UT_GREY} !important; }}

    /* Chat + cards */
    [data-testid="stChatMessage"] {{ background-color: {UT_LIGHT_GREY}; border-radius: 8px; }}
    [data-testid="stExpander"] {{ border-color: {UT_BORDER_GREY}; }}
    [data-testid="stProgress"] div[role="progressbar"] > div {{ background-color: {UT_ORANGE}; }}
</style>
"""

THEME_CSS = {"Light": LIGHT_CSS, "Dark": DARK_CSS, "UT Knoxville": UT_CSS}


def _ensure_theme():
    if st.session_state.get("theme") not in THEMES:
        st.session_state.theme = "Light"


def settings_menu():
    st.markdown(
        """
    <style>
        div[data-testid="stPopoverButton"] {
            position: fixed;
            top: 10px;
            right: 25px;
            z-index: 9999;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    _ensure_theme()
    with st.popover("⚙️"):
        # key="theme" writes the choice straight into session_state, so the
        # whole app (see app.py) re-renders with the new theme immediately.
        st.selectbox("Theme", THEMES, key="theme")
        if st.button("Logout"):
            api.logout_session()
            st.rerun()


def apply_theme():
    _ensure_theme()
    st.markdown(THEME_CSS[st.session_state.theme], unsafe_allow_html=True)
