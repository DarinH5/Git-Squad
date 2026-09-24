#Home Page
#Where users will search for products they want

#Stuff to do:
#Setting bar: maybe change theme from there
#Search/Chat bar for the ai agent
#Implement sidebar for navigation
#Create logo
import streamlit as st
col1, col2, col3 = st.columns([1,1,1])
with col2:
    st.image("images/shopping_cart.png", width = "content")

st.markdown("""
    <div style="
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        ">
        Welcome to the Shopping Assistant Website
    </div>
""", unsafe_allow_html=True)
st.text_area("Search for products", height=100)
