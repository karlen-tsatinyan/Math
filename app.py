import time

import streamlit as st
import extra_streamlit_components as stx

from authentication import (
    login,
    create_login_token,
    login_from_token,
    revoke_login_token,
    cleanup_expired_tokens,
)

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
# REMEMBER ME SETTINGS
# ==========================================

REMEMBER_COOKIE_NAME = "advanced_math_remember_me"
REMEMBER_ME_DAYS = 30

REMEMBER_ME_SECONDS = (
    REMEMBER_ME_DAYS
    * 24
    * 60
    * 60
)


# ==========================================
# COOKIE MANAGER
#
# IMPORTANT:
# DO NOT put CookieManager inside
# @st.cache_resource.
#
# CookieManager is a Streamlit widget/component.
# ==========================================

cookie_manager = stx.CookieManager(
    key="advanced_math_cookie_manager"
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

# --------------------------------------------------
# Prevent repeated Remember-Me checks during
# the same Streamlit session.
# --------------------------------------------------

if "remember_login_checked" not in st.session_state:
    st.session_state.remember_login_checked = False

# --------------------------------------------------
# Used so expired-token cleanup happens only once
# per Streamlit session.
# --------------------------------------------------

if "remember_tokens_cleaned" not in st.session_state:
    st.session_state.remember_tokens_cleaned = False


# ==========================================
# REMEMBER-ME TOKEN CLEANUP
# ==========================================

def cleanup_remember_tokens():

    if st.session_state.remember_tokens_cleaned:
        return

    try:

        cleanup_expired_tokens()

    except Exception:

        # Cleanup should never prevent the
        # portal from opening.
        pass

    st.session_state.remember_tokens_cleaned = True


# ==========================================
# RESTORE REMEMBERED LOGIN
# ==========================================

def restore_remembered_login():

    """
    Restore the user from the persistent browser
    Remember-Me cookie.

    IMPORTANT:
    There is intentionally NO rerun loop here.

    CookieManager is a browser component, so on a
    completely fresh browser session it can need a
    short moment to initialize.

    We wait only once and then continue normally.
    """

    if st.session_state.remember_login_checked:
        return

    # --------------------------------------------------
    # Give CookieManager a short moment to initialize.
    #
    # This is intentionally a SINGLE short wait.
    # There is NO repeated rerun.
    # --------------------------------------------------

    try:

        time.sleep(1.0)

    except Exception:
        pass

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

    except Exception:

        token = None

    # --------------------------------------------------
    # Mark the check complete AFTER the cookie read.
    # --------------------------------------------------

    st.session_state.remember_login_checked = True

    # --------------------------------------------------
    # No Remember-Me cookie
    # --------------------------------------------------

    if not token:
        return

    # --------------------------------------------------
    # Validate token against PostgreSQL
    # --------------------------------------------------

    try:

        user = login_from_token(token)

    except Exception:

        user = None

    # --------------------------------------------------
    # Valid token
    # --------------------------------------------------

    if user:

        st.session_state.user = user

        st.session_state.selected_course = (
            user.get("selected_course")
        )

        return

    # --------------------------------------------------
    # Invalid / expired / revoked token
    #
    # Remove it from browser.
    # --------------------------------------------------

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME,
            key="remember_me_delete_restore"
        )

    except Exception:

        pass


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

        remember_me = st.checkbox(
            "Remember me on this device",
            value=False
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

                try:

                    user = login(
                        username,
                        password
                    )

                except Exception:

                    st.error(
                        "Unable to sign in. Please try again."
                    )

                    return

            # ==========================================
            # INVALID LOGIN
            # ==========================================

            if not user:

                st.error(
                    "Incorrect username or password."
                )

                return

            # ==========================================
            # SUCCESSFUL LOGIN
            # ==========================================

            st.session_state.user = user

            st.session_state.selected_course = (
                user.get("selected_course")
            )

            # ==========================================
            # REMEMBER ME ENABLED
            # ==========================================

            if remember_me:

                try:

                    token = create_login_token(
                        user
                    )

                    if token:

                        cookie_manager.set(
                            REMEMBER_COOKIE_NAME,
                            token,
                            path="/",
                            max_age=REMEMBER_ME_SECONDS,
                            secure=True,
                            same_site="strict",
                            key="remember_me_set"
                        )

                except Exception:

                    st.warning(
                        "You are logged in, but "
                        "Remember Me could not be enabled "
                        "on this browser."
                    )

            # ==========================================
            # REMEMBER ME NOT SELECTED
            # ==========================================

            else:

                try:

                    existing_token = (
                        cookie_manager.get(
                            REMEMBER_COOKIE_NAME
                        )
                    )

                    if existing_token:

                        revoke_login_token(
                            existing_token
                        )

                        cookie_manager.delete(
                            REMEMBER_COOKIE_NAME,
                            key="remember_me_delete_login"
                        )

                except Exception:

                    pass

            # ==========================================
            # IMPORTANT:
            #
            # DO NOT WAIT FOR COOKIE CONFIRMATION.
            # DO NOT CREATE A PENDING STATE.
            # DO NOT LOOP WITH RERUN().
            #
            # Login immediately.
            # ==========================================

            st.success(
                "Welcome!"
            )

            st.rerun()


# ==========================================
# COURSE SELECTION
# ==========================================

def course_selection_screen():

    user = st.session_state.user

    courses = user.get(
        "courses",
        []
    )

    if not courses:

        st.error(
            "No course has been assigned to this student."
        )

        if st.button(
            "Logout",
            key="logout_no_course"
        ):

            logout_user()

        return

    if len(courses) == 1:

        st.session_state.selected_course = courses[0]

        st.rerun()

        return

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

                st.session_state.user[
                    "selected_course"
                ] = course

                st.rerun()

    st.divider()

    if st.button(
        "Logout",
        key="course_selection_logout"
    ):

        logout_user()


# ==========================================
# COMPACT SIDEBAR FOOTER
# ==========================================

def sidebar_footer(user):

    st.sidebar.divider()

    st.sidebar.markdown(
        f"👤 **{user['username']}**"
    )

    selected_course = st.session_state.get(
        "selected_course"
    )

    if selected_course:

        st.sidebar.caption(
            f"📘 Course: {selected_course}"
        )

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

            logout_user()

    if "refresh_message" in st.session_state:

        st.sidebar.success(
            st.session_state["refresh_message"]
        )

        del st.session_state[
            "refresh_message"
        ]


# ==========================================
# LOGOUT
# ==========================================

def logout_user():

    # ==========================================
    # GET CURRENT REMEMBER-ME TOKEN
    # ==========================================

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

    except Exception:

        token = None

    # ==========================================
    # REVOKE TOKEN IN DATABASE
    # ==========================================

    if token:

        try:

            revoke_login_token(
                token
            )

        except Exception:

            pass

    # ==========================================
    # DELETE BROWSER COOKIE
    # ==========================================

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME,
            key="remember_me_delete_logout"
        )

    except Exception:

        pass

    # ==========================================
    # CLEAR SESSION
    # ==========================================

    st.session_state.user = None

    st.session_state.selected_course = None

    st.session_state.remember_login_checked = False

    # ==========================================
    # CLEAR CACHED DATA
    # ==========================================

    st.cache_data.clear()

    if hasattr(
        st,
        "cache_resource"
    ):

        st.cache_resource.clear()

    # ==========================================
    # RETURN TO LOGIN
    # ==========================================

    st.rerun()


# ==========================================
# MAIN
# ==========================================

def main():

    # ==========================================
    # CLEAN OLD REMEMBER-ME TOKENS
    # ==========================================

    cleanup_remember_tokens()

    # ==========================================
    # TRY REMEMBER-ME LOGIN
    # ==========================================

    if st.session_state.user is None:

        restore_remembered_login()

    # ==========================================
    # SHOW LOGIN
    # ==========================================

    if st.session_state.user is None:

        login_screen()

        return

    # ==========================================
    # USER IS LOGGED IN
    # ==========================================

    user = st.session_state.user

    # ==========================================
    # ADMIN
    # ==========================================

    if user["role"] == "admin":

        admin_page()

        sidebar_footer(user)

        return

    # ==========================================
    # STUDENT
    # ==========================================

    courses = user.get(
        "courses",
        []
    )

    selected_course = st.session_state.get(
        "selected_course"
    )

    # ==========================================
    # MULTIPLE COURSES
    # ==========================================

    if len(courses) > 1 and not selected_course:

        course_selection_screen()

        return

    # ==========================================
    # ONE COURSE
    # ==========================================

    if len(courses) == 1 and not selected_course:

        st.session_state.selected_course = courses[0]

        user["selected_course"] = courses[0]

        st.rerun()

        return

    # ==========================================
    # NO COURSE
    # ==========================================

    if not selected_course:

        st.error(
            "No course has been assigned to this student."
        )

        sidebar_footer(user)

        return

    # ==========================================
    # STORE SELECTED COURSE
    # ==========================================

    user["selected_course"] = selected_course

    st.session_state.user = user

    # ==========================================
    # STUDENT PORTAL
    # ==========================================

    student_page()

    # ==========================================
    # SIDEBAR
    # ==========================================

    sidebar_footer(user)


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    main()
