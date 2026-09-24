#Deals with login logic and other stuff
import streamlit as st
#Where I should handle login checks

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False 

##def login(username, password):
def login():
    ##Markdown logic
    ##Uses HTML, use !important to override default styles
    st.markdown("""
        <style>
            .login_title {
                text-align: center;
                font-size: 7rem !important;
            }
        </style>
    <h1 class = "login_title">
        Login
    </h1>
    """, unsafe_allow_html=True)
    #Creates columns, number in array represent width of that column
    col1, col2, col3  = st.columns([1, 1 ,1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if (st.button("Press to Login")):
            #st.session_state.logged_in = True
            if (username == "admin" and password == "password"):
                st.session_state.logged_in = True
            else:
                st.write("Invalid username or password")
            st.rerun()
        if (st.button("Forgot Password?")):
            #pg = st.navigation([recover_page])
            #st.session_state.page = "recover_page"
            st.switch_page(recover_page)

def recover():
    st.markdown("""
        <style>
            .recover_title {
                text-align: center;
                font-size: 4rem !important;
            }
        </style>
    <h1 class = "recover_title">
        Recover Password
    </h1>
    """, unsafe_allow_html=True)
    email = st.text_input("Email/Username?")
    if st.button("Send Reset Link"):
        # Handle password reset logic here
        st.write("Reset link sent to your email.")
        pass
    if st.button("Back to Login"):
        st.switch_page(login_page)

def logout():
    st.session_state.logged_in = False
    st.rerun()

login_page = st.Page(login, title="Login")
logout_page = st.Page(logout, title="Logout")
recover_page = st.Page(recover, title="Recover Password")
home_page = st.Page("pages/home_page.py", title="Home", default=True )
project_page = st.Page("pages/projects_page.py", title="Project", )
profile = st.Page("pages/profile_page.py", title="Profile", )
faq_page = st.Page("pages/faq_page.py", title="FAQ", )

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Account": [profile,logout_page],
            "Home": [home_page,project_page],
            "Help": [faq_page]
        }
    )
else:
    #pg = st.navigation({"Welcome":[login_page, recover_page]})
    pg = st.navigation([login_page,recover_page])
pg.run()

