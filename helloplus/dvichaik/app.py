import streamlit as st

#Where I should handle login checks

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False 

##def login(username, password):
def login():
    st.title("Login")
    if (st.button("Press to Login")):
        st.session_state.logged_in = True
        st.rerun()
    # Replace this with your actual authentication logic
    #if username == "admin" and password == "password":
    #   st.session_state.logged_in = True
    #    st.success("Logged in successfully!")
    #else:
    #    st.error("Invalid username or password.")

def logout():
    st.session_state.logged_in = False
    st.rerun()

login_page = st.Page(login, title="Login")
logout_page = st.Page(logout, title="Logout")

home_page = st.Page("pages/Home.py", title="Home", default=True )

profile = st.Page("pages/Profile.py", title="Profile", )

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Account": [profile,logout_page],
            "Home": [home_page]
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()

