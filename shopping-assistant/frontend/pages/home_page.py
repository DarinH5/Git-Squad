import streamlit as st

import api
from components import product_cards

st.title("Shopping Assistant")
st.caption("Describe what you want in your own words, like “something warm for winter hikes under $100”.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Streamlit reruns the script on every interaction, so redraw the whole history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("products") is not None:
            product_cards(msg["products"], key_prefix=f"chat{i}")

if query := st.chat_input("What are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("Looking..."):
        r = api.post("/ai-search", body={"query": query, "limit": 3})
        if r.ok:
            data = r.json()
            products = data["results"]
            note = data.get("interpretation") or ""
            reply = note if products and note else (
                f"Here are {len(products)} matches." if products else "I couldn't find anything matching that."
            )
        elif r.status_code >= 500:
            # The AI isn't available (no API key, or Gemini had a problem): fall back to keyword search
            r = api.get("/search", q=query, limit=3)
            products = r.json()["results"] if r.ok else []
            reply = ("The AI assistant isn't available right now, so this is a basic keyword search."
                     if products else "The AI assistant isn't available, and the keyword search found nothing.")
        else:
            reply, products = f"Something went wrong ({r.status_code}).", None

    st.session_state.messages.append({"role": "assistant", "content": reply, "products": products})
    st.rerun()