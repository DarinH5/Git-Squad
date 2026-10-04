import html

import streamlit as st

import api_client as api
from components import apply_theme, settings_menu

BADGE_COLORS = {"High": "#2E7D32", "Medium": "#B26A00", "Low": "#C62828"}


def score_badge(score: int, label: str) -> str:
    color = BADGE_COLORS.get(label, "#58595B")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:0.85rem;font-weight:600;">'
        f"{score}/100 · {html.escape(label)}</span>"
    )


def show_results(item: str, results: list, min_score: int) -> None:
    shown = [r for r in results if r["score"] >= min_score]
    if not results:
        st.info(f"I couldn't find results for **{item}**. Try a broader product name.")
        return
    if not shown:
        st.info(f"No results for **{item}** meet your minimum score of {min_score}. Lower the slider to see them.")
        return

    st.markdown(f"### Results for {item}")
    for result in shown:
        # Titles come from the open web, so escape everything before using HTML.
        title = html.escape(result["title"])
        url = html.escape(result["url"], quote=True)
        st.markdown(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer"><b>{title}</b></a>'
            f"&nbsp; {score_badge(result['score'], result['label'])}",
            unsafe_allow_html=True,
        )
        st.caption(result["description"])
        with st.expander("Why this score?"):
            for reason in result["reasons"]:
                st.write(f"- {reason}")
            st.caption(
                "Heuristic based on the seller, listed ratings/reviews and warning signs "
                "in the search result. Always double-check before buying."
            )


settings_menu()
apply_theme()

st.title("Shopping Assistant")
st.write("Tell me what you want to buy and I’ll search the web and score each option for quality (0-100).")

min_score = st.slider(
    "Minimum quality score",
    0, 100, 0,
    help="Hide products scoring below this. Try 75+ to see only high-quality options.",
)

if "shopping_messages" not in st.session_state:
    st.session_state.shopping_messages = [
        {
            "role": "assistant",
            "content": "What are you shopping for today? Include a brand, budget, or preferred features if you have them.",
        }
    ]

for message in st.session_state.shopping_messages:
    with st.chat_message(message["role"]):
        if "results" in message:
            show_results(message["item"], message["results"], min_score)
        else:
            st.write(message["content"])

if prompt := st.chat_input("Search for a product..."):
    item = prompt.strip()
    if item:
        st.session_state.shopping_messages.append({"role": "user", "content": item})
        with st.chat_message("user"):
            st.write(item)

        with st.chat_message("assistant"):
            results = None
            with st.spinner("Searching the web..."):
                try:
                    results = api.search_products(item, st.session_state.token)
                except api.ApiError as err:
                    if err.status == 401:  # session expired or revoked
                        api.clear_session()
                        st.rerun()
                    st.error(str(err))

            if results is not None:
                show_results(item, results, min_score)
                st.session_state.shopping_messages.append(
                    {"role": "assistant", "item": item, "results": results}
                )
