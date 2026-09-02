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
REMEMBER_ME_MAX_AGE = REMEMBER_ME_DAYS * 24 * 60 * 60


# ==========================================
# COOKIE MANAGER
#
# IMPORTANT:
# DO NOT CACHE THIS COMPONENT.
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

    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    nav[data-testid="stSidebarNav"],
    section[data-testid="stSidebarNav"] {
        display: none !important;
    }

    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    header [data-testid="stDecoration"] {
        display: none !important;
    }

    footer {
        visibility: hidden;
    }

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

if "remember_cookie_checked" not in st.session_state:
    st.session_state.remember_cookie_checked = False

if "remember_cookie_waiting" not in st.session_state:
    st.session_state.remember_cookie_waiting = False

if "remember_cookie_pending_token" not in st.session_state:
    st.session_state.remember_cookie_pending_token = None

if "remember_tokens_cleaned" not in st.session_state:
    st.session_state.remember_tokens_cleaned = False


# ==========================================
# CLEAN EXPIRED TOKENS
# ==========================================

def cleanup_remember_tokens():

    if st.session_state.remember_tokens_cleaned:
        return

    try:
        cleanup_expired_tokens()
    except Exception:
        pass

    st.session_state.remember_tokens_cleaned = True


# ==========================================
# RESTORE REMEMBERED LOGIN
# ==========================================

def restore_remembered_login():

    """
    Restore the login from the persistent browser cookie.

    The function deliberately waits for the CookieManager
    component to initialize before treating a missing cookie
    as a real "no cookie" result.
    """

    if st.session_state.remember_cookie_checked:
        return True

    try:

        # --------------------------------------------------
        # Read all cookies.
        #
        # CookieManager may return None while its component
        # is still initializing.
        # --------------------------------------------------

        cookies = cookie_manager.get_all()

        if cookies is None:

            return False

        # --------------------------------------------------
        # Component is now responding.
        # --------------------------------------------------

        st.session_state.remember_cookie_checked = True

        token = cookies.get(
            REMEMBER_COOKIE_NAME
        )

        if not token:
            return True

        # --------------------------------------------------
        # Validate token against PostgreSQL.
        # --------------------------------------------------

        user = login_from_token(token)

        if user:

            st.session_state.user = user

            st.session_state.selected_course = (
                user.get("selected_course")
            )

            return True

        # --------------------------------------------------
        # Invalid/expired/revoked token.
        # --------------------------------------------------

        try:

            cookie_manager.delete(
                REMEMBER_COOKIE_NAME
            )

        except Exception:
            pass

        return True

    except Exception:
        # Cookie component is not ready yet.
        return False


# ==========================================
# SET REMEMBER-ME COOKIE
# ==========================================

def set_remember_me_cookie(token):

    """
    Put the persistent token into the browser.

    Returns True when the cookie command has been issued.
    """

    if not token:
        return False

    try:

        cookie_manager.set(
            REMEMBER_COOKIE_NAME,
            token,
            path="/",
            max_age=REMEMBER_ME_MAX_AGE,
            secure=True,
            same_site="strict"
        )

        return True

    except Exception:

        return False


# ==========================================
# REMOVE REMEMBER-ME COOKIE
# ==========================================

def remove_remember_me_cookie():

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME
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

            if not user:

                st.error(
                    "Incorrect username or password."
                )

                return

            # ==========================================
            # NORMAL SESSION LOGIN
            # ==========================================

            st.session_state.user = user

            st.session_state.selected_course = (
                user.get("selected_course")
            )

            # ==========================================
            # REMEMBER ME
            # ==========================================

            if remember_me:

                try:

                    token = create_login_token(
                        user
                    )

                    if not token:

                        raise RuntimeError(
                            "Unable to create login token."
                        )

                    # ----------------------------------
                    # Store token in session temporarily.
                    #
                    # This allows us to complete the
                    # browser-component round trip before
                    # proceeding.
                    # ----------------------------------

                    st.session_state.remember_cookie_pending_token = (
                        token
                    )

                    st.session_state.remember_cookie_waiting = (
                        True
                    )

                    # Issue browser cookie.
                    set_remember_me_cookie(token)

                    st.success(
                        "Welcome!"
                    )

                    # ----------------------------------
                    # Give CookieManager its own
                    # Streamlit/component cycle.
                    # ----------------------------------

                    st.rerun()

                except Exception:

                    st.warning(
                        "You are logged in, but "
                        "Remember Me could not be enabled "
                        "on this browser."
                    )

                    st.session_state.remember_cookie_pending_token = (
                        None
                    )

                    st.session_state.remember_cookie_waiting = (
                        False
                    )

                    st.rerun()

            else:

                # --------------------------------------
                # User did not select Remember Me.
                #
                # Remove any existing remembered token
                # for this browser.
                # --------------------------------------

                try:

                    existing_token = cookie_manager.get(
                        REMEMBER_COOKIE_NAME
                    )

                    if existing_token:

                        revoke_login_token(
                            existing_token
                        )

                except Exception:
                    pass

                remove_remember_me_cookie()

                st.success(
                    "Welcome!"
                )

                st.rerun()


# ==========================================
# FINISH PENDING REMEMBER-ME COOKIE
# ==========================================

def finish_pending_remember_me():

    """
    After login, allow CookieManager to complete its browser
    operation, then verify that the cookie is actually visible.

    This prevents the application from assuming that a cookie
    has been stored before the browser has processed it.
    """

    pending_token = (
        st.session_state.remember_cookie_pending_token
    )

    if not pending_token:
        st.session_state.remember_cookie_waiting = False
        return True

    try:

        cookies = cookie_manager.get_all()

        if cookies is None:
            return False

        saved_token = cookies.get(
            REMEMBER_COOKIE_NAME
        )

        if saved_token == pending_token:

            # ------------------------------------------
            # Cookie is now visible to the component.
            # ------------------------------------------

            st.session_state.remember_cookie_pending_token = (
                None
            )

            st.session_state.remember_cookie_waiting = (
                False
            )

            return True

        # --------------------------------------------------
        # Cookie has not reached the browser yet.
        # --------------------------------------------------

        set_remember_me_cookie(
            pending_token
        )

        return False

    except Exception:

        return False


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

    """
    Revoke the current browser token and delete the
    persistent browser cookie.
    """

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

    remove_remember_me_cookie()

    # ==========================================
    # CLEAR SESSION
    # ==========================================

    st.session_state.user = None

    st.session_state.selected_course = None

    st.session_state.remember_cookie_checked = False

    st.session_state.remember_cookie_waiting = False

    st.session_state.remember_cookie_pending_token = None

    # ==========================================
    # CLEAR APPLICATION CACHE
    # ==========================================

    st.cache_data.clear()

    if hasattr(
        st,
        "cache_resource"
    ):

        st.cache_resource.clear()

    st.rerun()


# ==========================================
# MAIN
# ==========================================

def main():

    # ==========================================
    # CLEAN EXPIRED TOKENS
    # ==========================================

    cleanup_remember_tokens()

    # ==========================================
    # COMPLETE A COOKIE SET DURING LOGIN
    # ==========================================

    if st.session_state.remember_cookie_waiting:

        cookie_ready = finish_pending_remember_me()

        if not cookie_ready:

            # --------------------------------------
            # CookieManager has not completed its
            # browser round-trip yet.
            # --------------------------------------

            st.info(
                "Signing you in..."
            )

            st.rerun()

            return

    # ==========================================
    # TRY REMEMBERED LOGIN
    # ==========================================

    if st.session_state.user is None:

        cookie_ready = restore_remembered_login()

        if not cookie_ready:

            # --------------------------------------
            # Wait for CookieManager to initialize.
            # --------------------------------------

            st.info(
                "Checking your saved login..."
            )

            st.rerun()

            return

    # ==========================================
    # NOT LOGGED IN
    # ==========================================

    if st.session_state.user is None:

        login_screen()

        return

    # ==========================================
    # CURRENT USER
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
    # STUDENT PORTAL
    # ==========================================

    user["selected_course"] = selected_course

    st.session_state.user = user

    student_page()

    # ==========================================
    # SIDEBAR
    # ==========================================

    sidebar_footer(user)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    main()
