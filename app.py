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


# ==========================================
# COOKIE MANAGER
#
# IMPORTANT:
# DO NOT cache CookieManager().
#
# CookieManager creates a Streamlit custom
# component/widget, so putting it inside
# @st.cache_resource causes CachedWidgetWarning.
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

# Prevent repeatedly checking the remember-me
# cookie during the same Streamlit session.
if "remember_login_checked" not in st.session_state:
    st.session_state.remember_login_checked = False

# Used so expired-token cleanup happens only once
# per Streamlit session.
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
        # Cleanup should never prevent the portal
        # from opening.
        pass

    st.session_state.remember_tokens_cleaned = True


# ==========================================
# RESTORE REMEMBERED LOGIN
# ==========================================

def restore_remembered_login():

    """
    Check the browser for the Remember Me token.

    The browser stores the random token.
    The database stores only its SHA-256 hash.

    If the token is valid, the user is automatically
    logged in without entering a password.
    """

    if st.session_state.remember_login_checked:
        return

    st.session_state.remember_login_checked = True

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

        if not token:
            return

        user = login_from_token(token)

        if user:

            # ------------------------------------------
            # Restore user
            # ------------------------------------------

            st.session_state.user = user

            # ------------------------------------------
            # Restore selected course
            #
            # authentication.py may already determine
            # selected_course when there is only one.
            # ------------------------------------------

            st.session_state.selected_course = (
                user.get("selected_course")
            )

            return

        # ----------------------------------------------
        # Invalid / expired token
        # ----------------------------------------------

        try:

            cookie_manager.delete(
                REMEMBER_COOKIE_NAME
            )

        except Exception:
            pass

    except Exception:
        # A cookie problem should never prevent the
        # normal login screen from appearing.
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

        # ----------------------------------------------
        # REMEMBER ME
        #
        # This is the ONLY new visible item on the
        # existing login interface.
        # ----------------------------------------------

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

                # ------------------------------------------
                # REMEMBER ME
                # ------------------------------------------

                if remember_me:

                    try:

                        # Create secure random token.
                        token = create_login_token(
                            user
                        )

                        # Store token in browser.
                        #
                        # secure=True:
                        # Only send cookie over HTTPS.
                        #
                        # same_site="strict":
                        # Restricts cross-site cookie use.
                        #
                        # max_age:
                        # 30 days.
                        #
                        cookie_manager.set(
                            REMEMBER_COOKIE_NAME,
                            token,
                            path="/",
                            max_age=(
                                REMEMBER_ME_DAYS
                                * 24
                                * 60
                                * 60
                            ),
                            secure=True,
                            same_site="strict"
                        )

                    except Exception:

                        # Login still works even if the
                        # persistent cookie cannot be created.
                        st.warning(
                            "You are logged in, but "
                            "Remember Me could not be enabled "
                            "on this browser."
                        )

                else:

                    # --------------------------------------
                    # User did NOT select Remember Me.
                    #
                    # If an older remembered cookie exists,
                    # revoke it and remove it.
                    # --------------------------------------

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
                                REMEMBER_COOKIE_NAME
                            )

                    except Exception:
                        pass

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

            logout_user()

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

        logout_user()


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

            logout_user()


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
# LOGOUT
# ==========================================

def logout_user():

    """
    Normal logout.

    The current Streamlit session is cleared and,
    if a Remember Me cookie exists, its database
    token is revoked and the browser cookie is deleted.
    """

    # ----------------------------------------------
    # Get existing remember-me token
    # ----------------------------------------------

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

        if token:

            revoke_login_token(
                token
            )

    except Exception:
        pass


    # ----------------------------------------------
    # Delete browser cookie
    # ----------------------------------------------

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME
        )

    except Exception:
        pass


    # ----------------------------------------------
    # Clear current session
    # ----------------------------------------------

    st.session_state.user = None

    st.session_state.selected_course = None

    st.session_state.remember_login_checked = False


    # ----------------------------------------------
    # Clear cached application data
    # ----------------------------------------------

    st.cache_data.clear()

    if hasattr(
        st,
        "cache_resource"
    ):

        st.cache_resource.clear()


    # ----------------------------------------------
    # Return to login
    # ----------------------------------------------

    st.rerun()


# ==========================================
# MAIN
# ==========================================

def main():

    # ======================================================
    # CLEAN EXPIRED REMEMBER-ME TOKENS
    # ======================================================

    cleanup_remember_tokens()


    # ======================================================
    # TRY REMEMBERED LOGIN
    #
    # This happens before displaying the login screen.
    # ======================================================

    if st.session_state.user is None:

        restore_remembered_login()


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
