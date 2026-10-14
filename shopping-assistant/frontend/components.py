import streamlit as st

import api

# Theme options shown in the settings menu. "UT Knoxville" = Tennessee Orange,
# White and Smokey Grey.
THEMES = ["Light", "Dark", "UT Knoxville"]

UT_ORANGE = "#FF8200"
UT_LIGHT_ORANGE = "#FFB347"
UT_GREY = "#4B4B4B"
UT_LIGHT_GREY = "#F2F2F2"
UT_WHITE = "#FFFFFF"
UT_TEST = "#3717B4"

DARK_CSS = """
<style>
    .stApp { background-color: #2e383d !important; color: white !important; }
    [data-testid="stSidebar"] { background-color: #1B262C !important; }
    h1, h2, h3, p, label { color: white !important; }
</style>
"""

LIGHT_CSS = """
<style>
    .stApp { background-color: #ceedfd !important; color: #889297 !important; }
    [data-testid="stSidebar"] { background-color: #9dd8f6 !important; }
    h1, h2, h3, p, label { color: #889297 !important; }
</style>
"""

UT_CSS = f"""
<style>
    .stApp {{ background-color: {UT_WHITE} !important; color: {UT_ORANGE} !important; }}
    [data-testid="stSidebar"] {{ background-color: {UT_WHITE} !important; }}
    [data-testid="stSidebar"] .stButton > button {{ background-color: {UT_LIGHT_GREY} !important; color: {UT_ORANGE} !important; }}
    h1, h2, h3, p, label {{ color: {UT_ORANGE} !important; }}
    [data-testid="stPopoverBody"] {{ background-color: {UT_WHITE} !important;
                                    color: {UT_ORANGE} !important; }}
    [data-testid="stPopoverButton"] {{ background-color: {UT_LIGHT_GREY} !important; color: {UT_ORANGE} !important; }}
    [data-testid="stTextInput"] input {{ background-color: {UT_LIGHT_GREY} !important; color: {UT_ORANGE} !important; outline: none !important; }}
    [data-testid="stTextInput"] input::placeholder {{ color: {UT_LIGHT_ORANGE} !important; }}
    [data-testid="st-emotion-cache-1tw7gkw"] {{background-color: none !important; }}

</style>
"""

THEME_CSS = {"Light": LIGHT_CSS, "Dark": DARK_CSS, "UT Knoxville": UT_CSS}


def _ensure_theme():
    if st.session_state.get("app_theme") not in THEMES:
        st.session_state.app_theme = "Dark"


def _update_theme():
    st.session_state.app_theme = st.session_state.theme_selector


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
    if st.session_state.get("theme_selector") not in THEMES:
        st.session_state.theme_selector = st.session_state.app_theme
    with st.popover("⚙️"):
        st.selectbox("Theme", THEMES, key="theme_selector", on_change=_update_theme)
        if st.button("Logout"):
            api.logout()
            st.rerun()


def apply_theme():
    _ensure_theme()
    st.markdown(THEME_CSS[st.session_state.app_theme], unsafe_allow_html=True)


def product_cards(products, per_row=3):
    """Show a list of product dictionaries as a grid of cards."""
    if not products:
        st.info("No products found. Try different words or loosen the filters.")
        return

    for start in range(0, len(products), per_row):
        row = products[start : start + per_row]
        cols = st.columns(per_row)
        for col, product in zip(cols, row):
            with col.container(border=True):
                if product.get("image_url"):
                    st.image(product["image_url"])
                st.markdown(f"**{product['title']}**")
                st.caption(
                    f"{product.get('brand') or ''} · "
                    f"{product.get('category') or ''}"
                )
                st.write(
                    f"**${product['price']:.2f}**  ·  "
                    f"⭐ {product['rating']}"
                )
                if product.get("description"):
                    st.write(product["description"])
                if product.get("product_url"):
                    st.link_button("View item", product["product_url"])
