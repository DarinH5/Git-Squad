import streamlit as st

import api


# Theme options shown in the settings menu. "UT Knoxville" = Tennessee Orange,
# White and Smokey Grey.
THEMES = ["Light", "Dark", "UT Knoxville"]

UT_ORANGE = "#FF8200"
UT_LIGHT_ORANGE = "#FFB347"
UT_LIGHT_GREY = "#F2F2F2"
UT_WHITE = "#FFFFFF"

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
    # Initialize valid saved and currently previewed theme values.
    if st.session_state.get("app_theme") not in THEMES:
        st.session_state.app_theme = "Dark"
    if st.session_state.get("saved_theme") not in THEMES:
        st.session_state.saved_theme = st.session_state.app_theme


def _preview_theme():
    # Apply the selected theme locally before it is persisted.
    st.session_state.app_theme = st.session_state.theme_selector


def _settings_popover_changed():
    # Restore the saved theme when the settings popover closes without saving.
    saved_theme = st.session_state.saved_theme
    st.session_state.theme_selector = saved_theme
    st.session_state.app_theme = saved_theme


def _start_theme_save():
    # Capture the selected theme and render the controls as disabled.
    st.session_state.theme_save_in_progress = True
    st.session_state.pending_theme = st.session_state.theme_selector
    st.rerun()


def _save_pending_theme():
    # Persist the captured theme and update the saved local baseline.
    selected_theme = st.session_state.pending_theme
    response = api.update_profile(theme=selected_theme)
    st.session_state.theme_save_in_progress = False
    st.session_state.pop("pending_theme", None)
    if not response.ok:
        st.error(f"Could not save your theme ({response.status_code}): {response.text}")
        return
    st.session_state.app_theme = selected_theme
    st.session_state.saved_theme = selected_theme
    st.success("Theme saved.")


def settings_menu():
    # Render theme controls and account actions in the settings popover.
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
    saving_theme = st.session_state.get("theme_save_in_progress", False)
    with st.popover("⚙️", key="settings_popover", on_change=_settings_popover_changed):
        st.selectbox(
            "Theme",
            THEMES,
            key="theme_selector",
            on_change=_preview_theme,
            disabled=saving_theme,
        )
        if st.session_state.theme_selector != st.session_state.saved_theme:
            st.button("Save theme", on_click=_start_theme_save, disabled=saving_theme)
        if st.button("Logout"):
            api.logout()
            st.rerun()
    if saving_theme:
        _save_pending_theme()


def apply_theme():
    # Inject the CSS for the current theme into the Streamlit page.
    _ensure_theme()
    st.markdown(THEME_CSS[st.session_state.app_theme], unsafe_allow_html=True)
    


def product_cards(products, per_row=3, key_prefix="browse", mode="browse", project_id=None):
    """Show a list of product dicts as a grid of cards.
 
    key_prefix: must differ for each call on the same page (each button needs a unique key).
    mode: "browse"  -> "Add to project" menu + View button (Browse and Chatbot pages)
          "project" -> Remove-from-project button + View button (Projects page; pass project_id)
    """
    if not products:
        st.info("No products found. Try different words or loosen the filters.")
        return
 
    # Fetch the user's projects once for the whole grid, not once per card
    projects = []
    if mode == "browse":
        pr = api.get("/projects")
        projects = pr.json() if pr.ok else []
    project_names = {p["id"]: p["name"] for p in projects}
 
    for start in range(0, len(products), per_row):
        row = products[start:start + per_row]
        cols = st.columns(per_row)  # always per_row columns so the last row stays aligned
        for col, p in zip(cols, row):
            with col.container(border=True):
                if p.get("image_url"):
                    st.image(p["image_url"])
                st.markdown(f"**{p['title']}**")
                st.caption(f"{p.get('brand') or ''} · {p.get('category') or ''}")
                st.write(f"**${p['price']:.2f}**  ·  ⭐ {p['rating']}")
                if p.get("description"):
                    st.write(p["description"])
 
                b1, b2 = st.columns(2)
                with b1:
                    if mode == "browse":
                        with st.popover("Add to project"):
                            if not projects:
                                st.caption("Create a project on the Projects page first.")
                            else:
                                pid = st.selectbox(
                                    "Project",
                                    [x["id"] for x in projects],
                                    format_func=lambda i: project_names[i],
                                    key=f"psel_{key_prefix}_{p['id']}",
                                )
                                if st.button("Add", key=f"padd_{key_prefix}_{p['id']}"):
                                    r = api.post(f"/projects/{pid}/items", product_id=p["id"])
                                    st.toast(r.json().get("message", "Added") if r.ok else "Couldn't add item")
                    elif mode == "project":
                        if st.button("Remove", key=f"premove_{key_prefix}_{p['id']}"):
                            api.delete(f"/projects/{project_id}/items/{p['id']}")
                            st.rerun()

