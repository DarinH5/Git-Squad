import streamlit as st
st.title("Git-Squad Demo Website" )
st.markdown("This is a demo website for the Git-Squad project. " \
"Our goal is to create a website to elevate the " \
":rainbow[shopping] experience of users")



search_query = st.sidebar.text_input("Search for products")
search_button = st.sidebar.button("Search")