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



#UI for displaying product cards
# Takes in the products from get request on the product page
# Puts them into a grid format and displays them.
def product_cards(products, per_row=3):
    """Show a list of product dicts as a grid of cards."""
    if not products:
        st.info("No products found. Try different words or loosen the filters.")
        return
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
                if p.get("product_url"):
                    st.link_button("View item", p["product_url"])
