import streamlit as st

from authentication import login
from pages.student import student_page
from pages.admin import admin_page


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    page_icon="📚",
    layout="wide"
)

st.set_option(
    "client.showErrorDetails",
    False
)


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


    /* =====================================================
       COURSE BUTTONS
       ===================================================== */

    .course-title {
        text-align: center;
        margin-bottom: 10px;
    }

    .course-subtitle {
        text-align: center;
        margin-bottom: 30px;
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

if "selected_course" not in st.session_state:
    st.session_state.selected_course = None


# ==========================================
# LOGIN SCREEN
# ==========================================

def login_screen():

    st.title(
        "📚 Advanced Math Tutoring Portal"
    )

    with st.form("login_form"):

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Login",
            type="primary"
        )

        if submitted:

            if not username.strip() or not password:

                st.error(
                    "Please enter your username and password."
                )

                return

            with st.spinner("Signing in..."):

                user = login(
                    username,
                    password
                )

            if user:

                # ------------------------------------------
                # SAVE USER
                # ------------------------------------------

                st.session_state.user = user

                # ------------------------------------------
                # SAVE AUTOMATICALLY SELECTED COURSE
                #
                # If there is only one course,
                # authentication.py already selected it.
                # ------------------------------------------

                st.session_state.selected_course = (
                    user.get("selected_course")
                )

                st.success(
                    "Welcome!"
                )

                st.rerun()

            else:

                st.error(
                    "Incorrect username or password."
                )


# ==========================================
# COURSE SELECTION
# ==========================================

def course_selection_screen():

    user = st.session_state.user

    courses = user.get(
        "courses",
        []
    )

    # ======================================================
    # SAFETY
    # ======================================================

    if not courses:

        st.error(
            "No course has been assigned to this student."
        )

        if st.button(
            "Logout",
            key="logout_no_course"
        ):

            st.session_state.user = None
            st.session_state.selected_course = None

            st.rerun()

        return


    # ======================================================
    # ONE COURSE
    #
    # This should normally already be handled by
    # authentication.py, but this protects the application.
    # ======================================================

    if len(courses) == 1:

        st.session_state.selected_course = courses[0]

        st.rerun()

        return


    # ======================================================
    # MULTIPLE COURSES
    # ======================================================

    st.markdown(
        '<h2 class="course-title">📚 Choose Your Course</h2>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<p class="course-subtitle">'
        'Please select the course you would like to enter.'
        '</p>',
        unsafe_allow_html=True
    )


    # ======================================================
    # COURSE BUTTONS
    # ======================================================

    # Create up to 3 columns at a time.
    # This keeps the layout clean if more courses are added.
    
    columns = st.columns(
        min(len(courses), 3)
    )


    for index, course in enumerate(courses):

        column = columns[
            index % len(columns)
        ]

        with column:

            if st.button(
                f"📘 {course}",
                use_container_width=True,
                type="primary",
                key=f"course_select_{index}"
            ):

                st.session_state.selected_course = course

                # ------------------------------------------
                # ALSO SAVE IT INSIDE USER
                # ------------------------------------------

                st.session_state.user[
                    "selected_course"
                ] = course

                st.rerun()


    # ======================================================
    # LOGOUT
    # ======================================================

    st.divider()

    if st.button(
        "Logout",
        key="course_selection_logout"
    ):

        st.session_state.user = None
        st.session_state.selected_course = None

        st.rerun()


# ==========================================
# COMPACT SIDEBAR FOOTER
# ==========================================

def sidebar_footer(user):

    st.sidebar.divider()

    # ======================================================
    # USERNAME
    # ======================================================

    st.sidebar.markdown(
        f"👤 **{user['username']}**"
    )


    # ======================================================
    # COURSE
    # ======================================================

    selected_course = st.session_state.get(
        "selected_course"
    )

    if selected_course:

        st.sidebar.caption(
            f"📘 Course: {selected_course}"
        )


    # ======================================================
    # BUTTONS
    # ======================================================

    col1, col2 = st.sidebar.columns(2)


    with col1:

        if st.button(
            "🔄 Refresh",
            use_container_width=True,
            key="global_refresh"
        ):

            st.cache_data.clear()

            if hasattr(
                st,
                "cache_resource"
            ):

                st.cache_resource.clear()

            st.session_state[
                "refresh_message"
            ] = (
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
            st.session_state.selected_course = None

            st.cache_data.clear()

            if hasattr(
                st,
                "cache_resource"
            ):

                st.cache_resource.clear()

            st.rerun()


    # ======================================================
    # REFRESH MESSAGE
    # ======================================================

    if "refresh_message" in st.session_state:

        st.sidebar.success(
            st.session_state["refresh_message"]
        )

        del st.session_state[
            "refresh_message"
        ]


# ==========================================
# MAIN
# ==========================================

def main():

    # ======================================================
    # NOT LOGGED IN
    # ======================================================

    if st.session_state.user is None:

        login_screen()

        return


    # ======================================================
    # CURRENT USER
    # ======================================================

    user = st.session_state.user


    # ======================================================
    # ADMIN
    # ======================================================

    if user["role"] == "admin":

        admin_page()

        sidebar_footer(user)

        return


    # ======================================================
    # STUDENT
    # ======================================================

    courses = user.get(
        "courses",
        []
    )

    selected_course = st.session_state.get(
        "selected_course"
    )


    # ======================================================
    # STUDENT WITH MULTIPLE COURSES
    #
    # Example:
    #
    # courses = ["Algebra", "Geometry"]
    # selected_course = None
    #
    # Show course selection screen.
    # ======================================================

    if len(courses) > 1 and not selected_course:

        course_selection_screen()

        return


    # ======================================================
    # STUDENT WITH ONE COURSE
    # ======================================================

    if len(courses) == 1 and not selected_course:

        st.session_state.selected_course = courses[0]

        user["selected_course"] = courses[0]

        st.rerun()

        return


    # ======================================================
    # NO COURSE ASSIGNED
    # ======================================================

    if not selected_course:

        st.error(
            "No course has been assigned to this student."
        )

        sidebar_footer(user)

        return


    # ======================================================
    # STUDENT PORTAL
    #
    # At this point:
    #
    # student_id = user["student_id"]
    # selected_course = "Algebra"
    #
    # or:
    #
    # selected_course = "Geometry"
    # ======================================================

    # Keep the selected course available to all
    # student-page modules.

    user["selected_course"] = selected_course

    st.session_state.user = user

    student_page()


    # ======================================================
    # SIDEBAR FOOTER
    # ======================================================

    sidebar_footer(user)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    main()
