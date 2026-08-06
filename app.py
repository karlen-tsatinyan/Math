import streamlit as st

from authentication import login
from pages.admin import admin_page
from pages.student import student_page
from supabase_client import get_supabase

# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    page_icon="📚",
    layout="wide"
)

st.set_option("client.showErrorDetails", False)

import time

APP_START = time.perf_counter()


# ==========================================
# HIDE STREAMLIT RUNNING INDICATORS
# ==========================================

st.markdown(
    """
    <style>

    /* Hide Streamlit automatic page navigation */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Hide status / running indicator */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* Hide top decoration */
    header [data-testid="stDecoration"] {
        display: none !important;
    }

    /* Hide footer */
    footer {
        visibility: hidden;
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
    # Refresh Data
    # -------------------------------

    st.sidebar.divider()

    if st.sidebar.button(
        "🔄 Refresh Data",
        use_container_width=True,
        key="global_refresh"
    ):

        st.cache_data.clear()

        st.session_state["refresh_message"] = (
            "✅ Data refreshed successfully."
        )

        st.rerun()


    if "refresh_message" in st.session_state:

        st.sidebar.success(
            st.session_state["refresh_message"]
        )

        del st.session_state["refresh_message"]


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

    APP_END = time.perf_counter()
    
    st.sidebar.caption(
        f"Page load: {APP_END - APP_START:.2f} seconds"
    )

