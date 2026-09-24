#User profile page
#User can view their profile information and edit it if they want
#Maybe users add a bio, which is fed to chatbot to tailor selections to their preferences

#Had to use ai to figure out how to get this working
import streamlit as st
import base64

#Turns the binary image date into text that html can read/access
#Need this because html src expects an url of some sort
def show_profile_picture():
    with open("images/shopping_cart.png", "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.markdown(f"""
        <style>
            .profile-pic {{
                position: fixed;
                top: 20px;
                right: 25px;
                width: 100px;
                height: 100px;
                border-radius: 80%;
                object-fit: cover;
                z-index: 9999;

                border: 2px solid #ccc;
            }}
        </style>

        <img class="profile-pic"
             src="data:images/shopping_cart.png;base64,{encoded}">
    """, unsafe_allow_html=True)

    #Title HTML
    st.markdown("""
        <style>
            .profile_title {
                text-align: left;
                font-size: 4rem !important;
            }
        </style>
        <h1 class = "profile_title">
        Profile
        </h1>
    """, unsafe_allow_html=True)

    st.text_area("Bio", value="Tell us about yourself.", height=100)

show_profile_picture()