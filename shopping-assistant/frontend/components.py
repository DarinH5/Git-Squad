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
:root { --accent: #8b9cf7; }
.stApp { background: #0b1020; color: #e8ecf8; }
[data-testid="stSidebar"] { background: #10182b; border-right: 1px solid #26314b; }
h1,h2,h3 { color: #f4f6ff !important; letter-spacing: -0.025em; }
p, label, .stMarkdown { color: #d5dcef; }
[data-testid="stMetric"] { background: #151f35; border: 1px solid #2b3857; padding: 14px; border-radius: 14px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2b3857 !important; border-radius: 16px; }
.stButton > button, .stFormSubmitButton > button { border-radius: 10px; border: 1px solid #3c4c73; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: #6578e8; color: white; border: 0; }
[data-testid="stChatMessage"] { background: #121b30; border: 1px solid #25324e; border-radius: 16px; }
</style>
"""

LIGHT_CSS = """
<style>
.stApp { background: #f5f7fc; color: #182238; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e4e9f2; }
h1,h2,h3 { color: #182238 !important; letter-spacing: -0.025em; }
p,label { color: #3c4961; }
[data-testid="stMetric"] { background: white; border: 1px solid #e4e9f2; padding: 14px; border-radius: 14px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #e1e7f0 !important; border-radius: 16px; }
.stButton > button, .stFormSubmitButton > button { border-radius: 10px; }
[data-testid="stChatMessage"] { background: white; border: 1px solid #e4e9f2; border-radius: 16px; }
</style>
"""

UT_CSS = """
<style>
.stApp { background: #fffaf4; color: #262626; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #f0dfce; }
h1,h2,h3 { color: #252525 !important; letter-spacing: -0.025em; }
[data-testid="stMetric"] { background: white; border: 1px solid #f0dfce; padding: 14px; border-radius: 14px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #f0dfce !important; border-radius: 16px; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: #ff8200; color: white; border: 0; }
[data-testid="stChatMessage"] { background: white; border: 1px solid #f0dfce; border-radius: 16px; }
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
                price = p.get("price")
                rating = p.get("rating")
                st.write(f"**${price:,.2f}**" if isinstance(price, (int, float)) else "**Price unavailable**")
                if rating is not None:
                    st.caption(f"⭐ {rating}/5")
                if p.get("personalization_reasons"):
                    st.caption(" · ".join(p["personalization_reasons"]))
                if p.get("description"):
                    st.write(p["description"])
                if p.get("product_url"):
                    st.markdown(f"[View product ↗]({p['product_url']})")
 
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

def show_recovery_code(code, button_key):
    """Display the code until the user confirms they saved it. Returns True once dismissed."""
    st.warning("Save your recovery code now. It's the only way to reset your password if you forget it, "
               "and it won't be shown again.")
    st.code(code, language=None)
    if st.button("I've saved it", key=button_key):
        return True
    return False

