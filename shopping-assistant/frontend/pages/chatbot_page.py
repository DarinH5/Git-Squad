"""Saved searches: revisit a useful shopping request without retyping it."""
import streamlit as st
import api

st.title("Saved searches")
st.caption("Keep useful shopping requests and run them again whenever you need.")

try:
    response = api.get_saved_searches()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if not response.ok:
    st.error("Couldn't load saved searches. Please try again.")
    st.stop()

saved = response.json()
if not saved:
    st.info("You haven't saved any searches yet. Run a search in AI Shopping and save it from the results.")
else:
    for item in saved:
        with st.container(border=True):
            left, run_col, delete_col = st.columns([5, 1, 1])
            left.markdown(f"**{item['query']}**")
            left.caption(f"Saved {item.get('created_at') or ''}")
            if run_col.button("Run", key=f"run_saved_{item['id']}", use_container_width=True):
                st.session_state.pending_shopping_query = item["query"]
                st.switch_page("pages/home_page.py")
            if delete_col.button("Delete", key=f"delete_saved_{item['id']}", use_container_width=True):
                result = api.delete_saved_search(item["id"])
                if result.ok:
                    st.rerun()
                st.error("Couldn't delete that saved search.")
