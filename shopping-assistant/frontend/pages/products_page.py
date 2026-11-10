import streamlit as st

import api
from components import product_cards

st.title("Explore products")
st.caption("Search the catalog and narrow results by category and budget.")

cat_response = api.get("/categories")
categories = cat_response.json() if cat_response.ok else []
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    query = c1.text_input("Search products", placeholder="e.g. wireless earbuds")
    category = c2.selectbox("Category", ["All categories"] + categories)
    max_price = c3.number_input("Max price ($)", min_value=0, value=0, step=10)
    search_clicked = st.button("Search catalog", type="primary", use_container_width=True)

params = {"q": query, "category": None if category == "All categories" else category,
          "max_price": max_price or None, "limit": 24}
# Keep the catalog immediately useful on first load; filters update on submit.
if "browse_query" not in st.session_state:
    st.session_state.browse_query = params
if search_clicked:
    st.session_state.browse_query = params

r = api.get("/search", **st.session_state.browse_query)
if r.ok:
    data = r.json()
    st.caption(f"{len(data['results'])} products · recommendations may reflect your saved profile")
    product_cards(data["results"], per_row=3, key_prefix="browse")
else:
    st.error(f"Search failed ({r.status_code}): {r.text}")
