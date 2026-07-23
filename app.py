import streamlit as st

from authentication import login
from pages.admin import admin_page
from pages.student import student_page


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    page_icon="📚",
    layout="wide"
)

st.set_option("client.showErrorDetails", False)


# ==========================================
# HIDE STREAMLIT RUNNING INDICATORS
# ==========================================

st.markdown(
    """
    <style>

    [data-testid="stStatusWidget"]{
        display:none !important;
    }

    header [data-testid="stDecoration"]{
        display:none !important;
    }

    footer{
        visibility:hidden;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================
# SESSION STATE
# ==========================================

if "user" not in st.session_state:
    st.session_state.user = None


# ==========================================
# LOGIN
# ==========================================

def login_screen():

    st.title("📚 Advanced Math Tutoring Portal")

    with st.form("login_form"):

        username = st.text_input("Username")

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button("Login")

        if submitted:

            with st.spinner("Signing in..."):

                user = login(
                    username,
                    password
                )

            if user:

                st.session_state.user = user

                st.success("Welcome!")

                st.rerun()

            else:

                st.error(
                    "Incorrect username or password."
                )


# ==========================================
# MAIN
# ==========================================

def main():

    if st.session_state.user is None:

        login_screen()

        return


    user = st.session_state.user


    st.sidebar.success(
        f"Logged in as\n\n**{user['username']}**"
    )


    # -------------------------------
    # Refresh button
    # -------------------------------

    if st.sidebar.button(
        "🔄 Refresh Data",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


    # -------------------------------
    # Logout
    # -------------------------------

    if st.sidebar.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.user = None

        st.cache_data.clear()

        st.rerun()


    # -------------------------------
    # Load Pages
    # -------------------------------

    with st.spinner("Loading..."):

        if user["role"] == "admin":

            admin_page()

        else:

            student_page()


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    main()
