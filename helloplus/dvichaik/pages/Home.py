import streamlit as st
st.title("Git-Squad Demo Website", text_alignment="center")
st.markdown("""
<style>
    textarea { font-size: 1.25rem !important; }

    [data-testid="stSidebar"] label{
        font-size: 10.25rem !important;
    }
    [data-testid="stSidebar"] input{
        font-size: 2.25rem !important;
    }
    [data-testid="stNavSectionHeader"]{
        font-size: 2.25rem !important;
    }

    

</style>""",
    unsafe_allow_html=True
)
st.text_area("What kind of product are you looking for?")
#Search = st.text_input("What kind of product are you looking for?")



search_query = st.sidebar.text_input("Search for products")
search_button = st.sidebar.button("Search")