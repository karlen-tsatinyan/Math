import streamlit as st

from authentication import login
from pages.admin import admin_page
from pages.student import student_page

from supabase_client import get_supabase

st.title("Supabase Homework File Test")

try:
    supabase = get_supabase()

    bucket_name = "homework-files"

    st.success("✅ Supabase connected")

    # Check bucket
    buckets = supabase.storage.list_buckets()

    if any(b.name == bucket_name for b in buckets):
        st.success("✅ homework-files bucket found")
    else:
        st.error("❌ homework-files bucket not found")

    # List files
    st.subheader("Files in assignments/student_1")

    files = supabase.storage.from_(bucket_name).list(
        "assignments/student_1"
    )

    if files:
        st.success(f"✅ Found {len(files)} item(s)")

        for file in files:
            st.write(file)

            file_name = file.get("name")

            if file_name:
                storage_path = (
                    f"assignments/student_1/{file_name}"
                )

                st.write("Storage path:", storage_path)

                public_url = supabase.storage.from_(
                    bucket_name
                ).get_public_url(
                    storage_path
                )

                st.write("Public URL:")
                st.code(public_url)

                st.link_button(
                    "🔗 Open Assignment",
                    public_url
                )

    else:
        st.warning(
            "No files were found in assignments/student_1."
        )

except Exception as e:
    st.error("❌ Supabase Storage test failed")
    st.exception(e)

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
    # Refresh button
    # -------------------------------

    if st.sidebar.button(
        "🔄 Refresh Data",
        use_container_width=True
    ):
        # Set a flag to force data reload on the next fetch
        st.session_state.force_refresh = True
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

APP_END = time.perf_counter()

st.sidebar.caption(
    f"Page load: {APP_END - APP_START:.2f} seconds"
)

