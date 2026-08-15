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
# + COMPACT SIDEBAR
# ==========================================

st.markdown(
    """
    <style>

    /* =====================================================
       HIDE STREAMLIT AUTOMATIC PAGE NAVIGATION
       ===================================================== */

    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    nav[data-testid="stSidebarNav"],
    section[data-testid="stSidebarNav"] {
        display: none !important;
    }


    /* =====================================================
       HIDE STATUS / RUNNING INDICATOR
       ===================================================== */

    [data-testid="stStatusWidget"] {
        display: none !important;
    }


    /* =====================================================
       HIDE TOP DECORATION
       ===================================================== */

    header [data-testid="stDecoration"] {
        display: none !important;
    }


    /* =====================================================
       HIDE FOOTER
       ===================================================== */

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
# COMPACT SIDEBAR FOOTER
# ==========================================

def sidebar_footer(user):

    st.sidebar.divider()

    st.sidebar.markdown(
        f"👤 **{user['username']}**"
    )

    col1, col2 = st.sidebar.columns(2)

    with col1:

        if st.button(
            "🔄 Refresh",
            use_container_width=True,
            key="global_refresh"
        ):

            st.cache_data.clear()

            st.session_state["refresh_message"] = (
                "✅ Data refreshed successfully."
            )

            st.rerun()

    with col2:

        if st.button(
            "Logout",
            use_container_width=True,
            key="global_logout"
        ):

            st.session_state.user = None

            st.cache_data.clear()

            st.rerun()


    if "refresh_message" in st.session_state:

        st.sidebar.success(
            st.session_state["refresh_message"]
        )

        del st.session_state["refresh_message"]


# ==========================================
# MAIN
# ==========================================

def main():
    st.error("🚨 APP.PY IS RUNNING THIS VERSION")


    if st.session_state.user is None:

        login_screen()

        return


    user = st.session_state.user


    # ==========================================
    # LOAD PAGES
    # ==========================================

    with st.spinner("Loading..."):

        if user["role"] == "admin":

            admin_page()

        else:

            student_page()


    # ==========================================
    # COMPACT SIDEBAR FOOTER
    # ==========================================

    sidebar_footer(user)

# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    main()

    APP_END = time.perf_counter()

    st.sidebar.caption(
        f"Page load: {APP_END - APP_START:.2f} seconds"
    )
