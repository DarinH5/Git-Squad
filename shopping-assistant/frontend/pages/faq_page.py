import streamlit as st

st.title("Help & frequently asked questions")
st.caption("A quick guide to how Shopwise AI works.")

with st.expander("How is AI Shopping different from Browse Products?", expanded=True):
    st.write(
        "Browse Products searches the catalog using the filters you choose. "
        "AI Shopping interprets a natural-language request, applies your saved shopping "
        "preferences, searches the same catalog, and explains how its agents ranked the results."
    )

with st.expander("Does the assistant work without Gemini?"):
    st.write(
        "Yes. The app uses a built-in intent parser and recommendation workflow when Gemini "
        "is not configured or temporarily unavailable. Gemini can improve interpretation, "
        "but it is not required for basic shopping search."
    )

with st.expander("Are product prices and availability live?"):
    st.write(
        "The current catalog contains demonstration products stored in the app database. "
        "Prices and availability are not guaranteed to be current. A licensed retailer data "
        "provider must be connected before treating results as live inventory."
    )

with st.expander("How do I personalize recommendations?"):
    st.write(
        "Open My Profile and add a budget, preferred categories and brands, brands to avoid, "
        "retailers, and shopping interests. The recommendation score uses these signals and "
        "shows reasons on matching product cards."
    )

with st.expander("Can I save a product or a search?"):
    st.write(
        "Use Add to project on a product card to keep products in a collection. "
        "Use Saved Searches to keep a shopping request and run it again later."
    )

with st.expander("How do I recover my account?"):
    st.write(
        "At this stage, password recovery uses the one-time recovery code shown when your "
        "account is created or when you generate a replacement. Keep it somewhere safe. "
        "Email-based recovery is a recommended production improvement."
    )
