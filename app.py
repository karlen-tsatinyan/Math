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
# HIDE STREAMLIT UI ELEMENTS
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

            with st.spinner(
                "Signing in..."
            ):

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
                # ADMIN
                # ------------------------------------------

                if user["role"] == "admin":

                    st.success(
                        "Welcome!"
                    )

                    st.rerun()

                # ------------------------------------------
                # STUDENT
                # ------------------------------------------

                else:

                    courses = user.get(
                        "courses",
                        []
                    )

                    # --------------------------------------
                    # NO COURSE ASSIGNED
                    # --------------------------------------

                    if len(courses) == 0:

                        st.warning(
                            "Your account is active, "
                            "but no course has been assigned yet. "
                            "Please contact your teacher."
                        )

                        return

                    # --------------------------------------
                    # ONE COURSE
                    #
                    # authentication.py already sets:
                    #
                    # selected_course = course
                    #
                    # So we can go directly to the portal.
                    # --------------------------------------

                    if len(courses) == 1:

                        st.session_state.user[
                            "selected_course"
                        ] = courses[0]

                        st.success(
                            f"Welcome! "
                            f"Opening {courses[0]}..."
                        )

                        st.rerun()

                    # --------------------------------------
                    # MULTIPLE COURSES
                    #
                    # Stay on the login/course screen.
                    # --------------------------------------

                    else:

                        st.rerun()

            else:

                st.error(
                    "Incorrect username or password."
                )


# ==========================================
# COURSE SELECTION
# ==========================================

def course_selection():

    user = st.session_state.user

    courses = user.get(
        "courses",
        []
    )

    # ======================================================
    # SAFETY CHECK
    # ======================================================

    if not courses:

        st.error(
            "No courses are assigned to this account."
        )

        if st.button(
            "Logout",
            key="course_logout_no_courses"
        ):

            st.session_state.user = None

            st.rerun()

        return


    # ======================================================
    # IF ONLY ONE COURSE
    # ======================================================

    if len(courses) == 1:

        st.session_state.user[
            "selected_course"
        ] = courses[0]

        st.rerun()

        return


    # ======================================================
    # MULTIPLE COURSES
    # ======================================================

    st.title(
        "📚 Choose Your Course"
    )

    st.write(
        f"Welcome, **{user['username']}**!"
    )

    st.write(
        "Please select the course you would like to open."
    )

    st.markdown(
        "---"
    )


    # ======================================================
    # COURSE BUTTONS
    # ======================================================

    columns = st.columns(
        len(courses)
    )


    for index, course in enumerate(courses):

        with columns[index]:

            # ----------------------------------------------
            # COURSE EMOJI
            # ----------------------------------------------

            course_lower = course.lower()

            if "algebra" in course_lower:

                icon = "📐"

            elif "geometry" in course_lower:

                icon = "📏"

            elif "precalculus" in course_lower:

                icon = "📈"

            elif "trigonometry" in course_lower:

                icon = "📊"

            else:

                icon = "📚"


            # ----------------------------------------------
            # COURSE BUTTON
            # ----------------------------------------------

            if st.button(
                f"{icon} {course}",
                use_container_width=True,
                type="primary",
                key=f"course_select_{index}"
            ):

                st.session_state.user[
                    "selected_course"
                ] = course

                st.rerun()


    st.markdown(
        "---"
    )


    # ======================================================
    # LOGOUT
    # ======================================================

    if st.button(
        "Logout",
        key="course_selection_logout"
    ):

        st.session_state.user = None

        st.cache_data.clear()

        if hasattr(
            st,
            "cache_resource"
        ):

            st.cache_resource.clear()

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
    # SHOW CURRENT COURSE FOR STUDENTS
    # ======================================================

    if user["role"] != "admin":

        selected_course = user.get(
            "selected_course"
        )

        if selected_course:

            st.sidebar.caption(
                f"📚 Course: {selected_course}"
            )


    # ======================================================
    # REFRESH / LOGOUT
    # ======================================================

    col1, col2 = st.sidebar.columns(2)


    with col1:

        if st.button(
            "🔄 Refresh",
            use_container_width=True,
            key="global_refresh"
        ):

            st.cache_data.clear()

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
            st.session_state[
                "refresh_message"
            ]
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
    # GET USER
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
    # STUDENT — NO COURSE SELECTED
    # ======================================================

    selected_course = user.get(
        "selected_course"
    )

    if not selected_course:

        course_selection()

        return


    # ======================================================
    # STUDENT PORTAL
    # ======================================================

    student_page()


    # ======================================================
    # SIDEBAR FOOTER
    # ======================================================

    sidebar_footer(user)


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    main()
