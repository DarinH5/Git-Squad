import streamlit as st

from components import apply_theme, settings_menu


def search_products(item: str) -> list[dict[str, str]]:
	from ddgs import DDGS

	query = f"{item} buy online price"
	results = DDGS().text(query, safesearch="moderate", max_results=6)
	return [
		{
			"title": result.get("title", "Shopping result"),
			"href": result.get("href", ""),
			"body": result.get("body", "No description available."),
		}
		for result in results
		if result.get("href")
	]


def show_results(item: str, results: list[dict[str, str]]) -> None:
	if not results:
		st.info(f"I couldn't find results for **{item}**. Try a broader product name.")
		return

	st.markdown(f"### Results for {item}")
	for result in results:
		st.markdown(f"**[{result['title']}]({result['href']})**")
		st.caption(result["body"])


settings_menu()
apply_theme()

st.title("Shopping Assistant")
st.write("Tell me what you want to buy and I’ll search the web for useful options.")

if "shopping_messages" not in st.session_state:
	st.session_state.shopping_messages = [
		{
			"role": "assistant",
			"content": "What are you shopping for today? Include a brand, budget, or preferred features if you have them.",
		}
	]

for message in st.session_state.shopping_messages:
	with st.chat_message(message["role"]):
		if message.get("results"):
			show_results(message["item"], message["results"])
		else:
			st.write(message["content"])

if prompt := st.chat_input("Search for a product..."):
	item = prompt.strip()
	if item:
		st.session_state.shopping_messages.append({"role": "user", "content": item})
		with st.chat_message("user"):
			st.write(item)

		with st.chat_message("assistant"):
			search_failed = False
			with st.spinner("Searching the web..."):
				try:
					results = search_products(item)
				except Exception:
					results = []
					search_failed = True
					st.error("The web search is unavailable right now. Please try again in a moment.")

			if results:
				show_results(item, results)
			elif not search_failed:
				st.info(f"I couldn't find results for **{item}**. Try a broader product name.")

		st.session_state.shopping_messages.append(
			{"role": "assistant", "item": item, "results": results}
		)
