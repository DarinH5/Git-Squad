#Home Page
#Where users will search for products they want

#Stuff to do:
#Setting bar: maybe change theme from there
#Search/Chat bar for the ai agent
#Implement sidebar for navigation
#Create logo

#import streamlit as st

#Blurred this code out so I could get basic app functionality done.
#In sprint 3, we will need to connect chatbot to home page so it can parse the 
# search input and provide relevant responses.
"""def open_chatbot() -> None:
	# Pass the home-page search text to the chatbot page.
    prompt = st.session_state.home_search.strip()
    if prompt:
        st.session_state.pending_chat_prompt = prompt
        st.session_state.scroll_to_latest_search = True
        st.switch_page("pages/chatbot_page.py")


col1, col2, col3 = st.columns([1,1,1])
with col2:
    st.image("images/shopping_cart.png", width = "content")

st.markdown(""a
    <div style="
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        ">
        Welcome to the Shopping Assistant Website
    </div>
""a, unsafe_allow_html=True)
st.text_input(
    "Search for products",
    placeholder="Enter product name",
    key="home_search",
    on_change=open_chatbot,
)
"""

import streamlit as st
 
import api
from components import product_cards
 
st.title(f"Welcome, {st.session_state.username}!")
st.write("Search for a product by name, category, or price.")
 
query = st.text_input(
    "Search",
    key="home_query",
    placeholder="e.g. waterproof boots under $100",
    label_visibility="collapsed",
)
st.caption("Still a work in progress.")
st.caption("Try: **boots**, **jackets under $100**, **between $50 and $80**, **backpack over 60**, **$30**")
 
# The text box keeps its value across reruns, so results stay on screen after clicking a card's buttons

# Perform the search if the query is not empty.
if query.strip():

    # Call the backend search API with the query and limit.
    r = api.get("/search", q=query, limit=9)
    if not r.ok:
        st.error(f"Search failed ({r.status_code})")
    else:

        # Get the JSON data from the response.
        # applied contains the filters that were applied to the search, including text, min_price, and max_price.
        data = r.json()
        applied = data["applied"]
 
        # Tell the user how their search was understood
        # example: "Showing 3 results: “waterproof boots”, from $50, up to $100"
        parts = []
        if applied["text"]:
            parts.append(f"“{applied['text']}”")
        if applied["min_price"] is not None:
            parts.append(f"from ${applied['min_price']:,.2f}")
        if applied["max_price"] is not None:
            parts.append(f"up to ${applied['max_price']:,.2f}")
        count = len(data["results"])
        st.caption(f"Showing {count} result{'s' if count != 1 else ''}" + (": " + ", ".join(parts) if parts else ""))
 
        product_cards(data["results"], key_prefix="home")
