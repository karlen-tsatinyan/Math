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
# Create CookieManager ONCE per Streamlit
# session.
#
# DO NOT use @st.cache_resource.
# DO NOT create a new CookieManager on
# every rerun.
# ==========================================

if "cookie_manager" not in st.session_state:

    st.session_state.cookie_manager = (
        stx.CookieManager(
            key="advanced_math_cookie_manager"
        )
    )

cookie_manager = st.session_state.cookie_manager


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

if "remember_login_checked" not in st.session_state:
    st.session_state.remember_login_checked = False

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
        # Cleanup must never prevent the portal
        # from opening.
        pass

    st.session_state.remember_tokens_cleaned = True


# ==========================================
# RESTORE REMEMBERED LOGIN
# ==========================================

def restore_remembered_login():

    """
    Restore the user from the persistent browser
    Remember-Me cookie.

    CookieManager loads the browser cookies when
    it is initialized. We use its cookie dictionary
    directly.

    There is intentionally NO time.sleep() here.
    """

    if st.session_state.remember_login_checked:
        return

    # ------------------------------------------------------
    # Mark this session as checked.
    # ------------------------------------------------------

    st.session_state.remember_login_checked = True

    # ------------------------------------------------------
    # Read the cookie from CookieManager's loaded
    # cookie dictionary.
    # ------------------------------------------------------

    try:

        token = cookie_manager.cookies.get(
            REMEMBER_COOKIE_NAME
        )

    except Exception:

        token = None

    # ------------------------------------------------------
    # No Remember-Me cookie.
    # ------------------------------------------------------

    if not token:
        return

    # ------------------------------------------------------
    # Validate token against PostgreSQL.
    # ------------------------------------------------------

    try:

        user = login_from_token(token)

    except Exception:

        user = None

    # ------------------------------------------------------
    # Valid token.
    # ------------------------------------------------------

    if user:

        st.session_state.user = user

        st.session_state.selected_course = (
            user.get("selected_course")
        )

        return

    # ------------------------------------------------------
    # Invalid / expired / revoked token.
    #
    # Remove it from the browser.
    # ------------------------------------------------------

    try:

        revoke_login_token(token)

    except Exception:
        pass

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME,
            key="remember_me_delete_invalid"
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

        if not submitted:
            return

        # --------------------------------------------------
        # Validate fields
        # --------------------------------------------------

        if not username.strip() or not password:

            st.error(
                "Please enter your username and password."
            )

            return

        # --------------------------------------------------
        # NORMAL LOGIN
        #
        # No artificial sleep.
        # --------------------------------------------------

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

        # --------------------------------------------------
        # INVALID LOGIN
        # --------------------------------------------------

        if not user:

            st.error(
                "Incorrect username or password."
            )

            return

        # --------------------------------------------------
        # SAVE USER IN CURRENT STREAMLIT SESSION
        # --------------------------------------------------

        st.session_state.user = user

        st.session_state.selected_course = (
            user.get("selected_course")
        )

        # ==================================================
        # REMEMBER ME ENABLED
        # ==================================================

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

        # ==================================================
        # REMEMBER ME NOT SELECTED
        # ==================================================

        else:

            try:

                existing_token = (
                    cookie_manager.cookies.get(
                        REMEMBER_COOKIE_NAME
                    )
                )

            except Exception:

                existing_token = None

            if existing_token:

                try:

                    revoke_login_token(
                        existing_token
                    )

                except Exception:
                    pass

                try:

                    cookie_manager.delete(
                        REMEMBER_COOKIE_NAME,
                        key="remember_me_delete_login"
                    )

                except Exception:
                    pass

        # ==================================================
        # LOGIN COMPLETE
        #
        # Immediately rerun so main() sees the authenticated
        # user and opens the correct portal.
        # ==================================================

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

    # ======================================================
    # NO COURSE
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
    # ======================================================

    if len(courses) == 1:

        st.session_state.selected_course = courses[0]

        user["selected_course"] = courses[0]

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

    # ======================================================
    # GET CURRENT REMEMBER-ME TOKEN
    # ======================================================

    try:

        token = cookie_manager.cookies.get(
            REMEMBER_COOKIE_NAME
        )

    except Exception:

        token = None

    # ======================================================
    # REVOKE TOKEN
    # ======================================================

    if token:

        try:

            revoke_login_token(
                token
            )

        except Exception:
            pass

    # ======================================================
    # DELETE BROWSER COOKIE
    # ======================================================

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME,
            key="remember_me_delete_logout"
        )

    except Exception:
        pass

    # ======================================================
    # CLEAR SESSION
    # ======================================================

    st.session_state.user = None

    st.session_state.selected_course = None

    st.session_state.remember_login_checked = False

    # ======================================================
    # CLEAR CACHED DATA
    # ======================================================

    st.cache_data.clear()

    if hasattr(
        st,
        "cache_resource"
    ):

        st.cache_resource.clear()

    # ======================================================
    # RETURN TO LOGIN
    # ======================================================

    st.rerun()


# ==========================================
# MAIN
# ==========================================

def main():

    # ======================================================
    # CLEAN OLD TOKENS
    # ======================================================

    cleanup_remember_tokens()

    # ======================================================
    # TRY REMEMBERED LOGIN
    # ======================================================

    if st.session_state.user is None:

        restore_remembered_login()

    # ======================================================
    # LOGIN SCREEN
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
    # MULTIPLE COURSES
    # ======================================================

    if len(courses) > 1 and not selected_course:

        course_selection_screen()

        return

    # ======================================================
    # ONE COURSE
    # ======================================================

    if len(courses) == 1 and not selected_course:

        st.session_state.selected_course = courses[0]

        user["selected_course"] = courses[0]

        st.rerun()

        return

    # ======================================================
    # NO COURSE
    # ======================================================

    if not selected_course:

        st.error(
            "No course has been assigned to this student."
        )

        sidebar_footer(user)

        return

    # ======================================================
    # STORE SELECTED COURSE
    # ======================================================

    user["selected_course"] = selected_course

    st.session_state.user = user

    # ======================================================
    # STUDENT PORTAL
    # ======================================================

    student_page()

    # ======================================================
    # SIDEBAR
    # ======================================================

    sidebar_footer(user)


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    main()
