import streamlit as st
st.title("Projects Page")
st.markdown("Save items, and organize them into groups here!")
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