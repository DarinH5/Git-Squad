import streamlit as st

import api
from components import product_cards

st.title("Your AI shopping assistant")
st.caption("Tell the agents what you need. They will interpret your request, apply your preferences, and rank matching products.")

with st.container(border=True):
    st.markdown("**Try asking**")
    examples = [
        "Find wireless earbuds under $100",
        "I need a lightweight backpack for college",
        "Show me waterproof hiking gear",
    ]
    cols = st.columns(len(examples))
    for i, example in enumerate(examples):
        if cols[i].button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.pending_shopping_query = example

if "shopping_history" not in st.session_state:
    st.session_state.shopping_history = []

for index, message in enumerate(st.session_state.shopping_history):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("agents"):
            with st.expander("How your shopping agents worked", expanded=False):
                for agent in message["agents"]:
                    st.markdown(f"**{agent['name']}** · {agent['status'].title()}")
                    st.caption(agent["task"])
        if message.get("products") is not None:
            if message.get("personalized"):
                st.caption("✨ Ranked using your saved shopping profile")
            product_cards(message["products"], key_prefix=f"agent_chat_{index}")

query = st.session_state.pop("pending_shopping_query", None) or st.chat_input("What are you shopping for?")
if query and query.strip():
    query = query.strip()
    st.session_state.shopping_history.append({"role": "user", "content": query})
    with st.spinner("Your shopping agents are researching products..."):
        response = api.shop_with_agents(query, limit=9)
    if response.ok:
        data = response.json()
        products = data.get("results", [])
        reply = data.get("interpretation") or (
            f"I found {len(products)} matching products." if products else
            "I couldn't find a match. Try changing the product type or budget."
        )
        st.session_state.shopping_history.append({
            "role": "assistant",
            "content": reply,
            "products": products,
            "agents": data.get("agents", []),
            "personalized": data.get("personalized", False),
        })
    else:
        detail = response.json().get("detail", "The shopping service is unavailable.")
        st.session_state.shopping_history.append({
            "role": "assistant",
            "content": f"I couldn't complete that search: {detail}",
            "products": [],
        })
    st.rerun()
