import streamlit as st
 
import api
from components import product_cards
 
st.title("Products Page")
st.write("Placeholder to see if product cards are displayed correctly")
st.write("Could keep or delete depending on what we want to do")
# Filters

#Sends a get request to retrieve categories from main
#Creates three columns for search, category, and max price
#Displays products based on these columns
#Unused filters aren't sent in the request
categories = api.get("/categories").json()
c1, c2, c3 = st.columns([3, 2, 2])
query = c1.text_input("Search", placeholder="e.g. waterproof boots")
category = c2.selectbox("Category", ["All"] + categories)
max_price = c3.number_input("Max price ($)", min_value=0, value=0, step=10, help="0 means no limit")
 
# None values are dropped from the URL by requests, so unused filters are simply not sent

#Sends a GET request to the search endpoint in main
#   query comes from the search input
#   category comes from the category selectbox
#   max_price comes from the max price number input
r = api.get(
    "/search",
    q=query,
    category=None if category == "All" else category,
    max_price=max_price or None,
)
#if the request is valid, the product cards are displayed
if r.ok:
    product_cards(r.json()["results"])
else:
    st.error(f"Search failed ({r.status_code})")