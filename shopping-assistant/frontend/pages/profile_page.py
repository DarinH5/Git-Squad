#User profile page
#User can view their profile information and edit it if they want
#Maybe users add a bio, which is fed to chatbot to tailor selections to their preferences

#Had to use ai to figure out how to get this working
import streamlit as st
import base64

import api


def _load_bio():
    if st.session_state.get("profile_bio_loaded"):
        return st.session_state.get("bio", "")

    response = api.get("/me")
    if not response.ok:
        st.error(f"Could not load your description ({response.status_code}): {response.text}")
        return ""
    st.session_state.bio = response.json().get("bio", "")
    st.session_state.profile_bio_loaded = True
    return st.session_state.bio


def _start_bio_save():
    st.session_state.bio_save_in_progress = True
    st.session_state.pending_bio = st.session_state.bio_editor
    st.rerun()


def _save_pending_bio():
    response = api.update_profile(bio=st.session_state.pending_bio)
    st.session_state.bio_save_in_progress = False
    st.session_state.pop("pending_bio", None)
    if not response.ok:
        st.error(
            f"Could not save your description "
            f"({response.status_code}): {response.text}"
        )
        return False
    st.session_state.bio = response.json().get("bio", st.session_state.bio)
    st.session_state.profile_bio_loaded = True
    st.session_state.editing_bio = False
    st.session_state.bio_save_message = "Description saved."
    return True


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

    if st.session_state.pop("bio_save_message", None):
        st.success("Description saved.")

    saved_bio = _load_bio()
    if not st.session_state.get("editing_bio", False):
        st.text_area("Bio", value=saved_bio, height=100, disabled=True)
        if st.button("Edit bio"):
            st.session_state.editing_bio = True
            st.rerun()
    else:
        saving_bio = st.session_state.get("bio_save_in_progress", False)
        if saving_bio:
            st.session_state.bio_editor = st.session_state.pending_bio
        elif "bio_editor" not in st.session_state:
            st.session_state.bio_editor = saved_bio
        with st.form("profile_form"):
            bio = st.text_area(
                "Bio",
                placeholder="Tell us about yourself.",
                height=100,
                key="bio_editor",
                disabled=saving_bio,
            )
            st.form_submit_button(
                "Save description",
                on_click=_start_bio_save,
                disabled=saving_bio,
            )

        if saving_bio:
            if _save_pending_bio():
                st.rerun()

show_profile_picture()