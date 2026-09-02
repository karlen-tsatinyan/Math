import streamlit as st
import extra_streamlit_components as stx

from pages.admin import admin_page
from pages.student import student_page

from authentication import (
    login,
    create_login_token,
    login_from_token,
    revoke_login_token,
    cleanup_expired_tokens,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

REMEMBER_COOKIE_NAME = "advanced_math_remember_me"
REMEMBER_ME_DAYS = 30


# ============================================================
# COOKIE MANAGER
# IMPORTANT:
# DO NOT put CookieManager() inside @st.cache_resource
# because CookieManager creates a Streamlit widget.
# ============================================================

cookie_manager = stx.CookieManager(
    key="advanced_math_cookie_manager"
)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def initialize_session_state():

    if "user" not in st.session_state:
        st.session_state.user = None

    if "remember_me" not in st.session_state:
        st.session_state.remember_me = False

    if "login_checked" not in st.session_state:
        st.session_state.login_checked = False

    if "selected_course" not in st.session_state:
        st.session_state.selected_course = None

    if "tokens_cleaned" not in st.session_state:
        st.session_state.tokens_cleaned = False


# ============================================================
# CLEANUP EXPIRED TOKENS
# ============================================================

def cleanup_tokens_once():

    if st.session_state.tokens_cleaned:
        return

    try:

        cleanup_expired_tokens()

    except Exception:
        # Token cleanup should never prevent the application
        # from loading.
        pass

    st.session_state.tokens_cleaned = True


# ============================================================
# RESTORE REMEMBERED LOGIN
# ============================================================

def restore_remembered_login():

    """
    Try to restore the user's login from the browser cookie.

    The browser contains the raw token.
    The database contains only the SHA-256 hash.
    """

    if st.session_state.login_checked:
        return

    st.session_state.login_checked = True

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

        if not token:
            return

        user = login_from_token(token)

        if user:

            st.session_state.user = user
            st.session_state.remember_me = True

            # ------------------------------------------------
            # Automatically select a course if the student
            # only has one course.
            # ------------------------------------------------

            if user.get("role") == "student":

                courses = user.get(
                    "courses",
                    []
                )

                if len(courses) == 1:

                    st.session_state.selected_course = (
                        courses[0]
                    )

            return

        # ----------------------------------------------------
        # Token is invalid or expired.
        # Remove it from browser.
        # ----------------------------------------------------

        try:

            cookie_manager.delete(
                REMEMBER_COOKIE_NAME
            )

        except Exception:
            pass

    except Exception:
        # Do not prevent the login screen from opening.
        pass


# ============================================================
# LOGIN SCREEN
# ============================================================

def login_screen():

    st.markdown(
        """
        <style>

        .login-container {
            max-width: 500px;
            margin: 80px auto 0 auto;
            padding: 35px;
            border-radius: 15px;
            border: 1px solid rgba(128,128,128,0.25);
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .login-title {
            text-align: center;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .login-subtitle {
            text-align: center;
            font-size: 16px;
            color: #777;
            margin-bottom: 30px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-container">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-title">📐 Math Tutoring Portal</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-subtitle">Sign in to continue</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # USERNAME
    # --------------------------------------------------------

    username = st.text_input(
        "Username",
        key="login_username",
    )

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

    password = st.text_input(
        "Password",
        type="password",
        key="login_password",
    )

    # --------------------------------------------------------
    # REMEMBER ME
    # --------------------------------------------------------

    remember_me = st.checkbox(
        "Remember me on this device",
        value=False,
        key="login_remember_me",
    )

    # --------------------------------------------------------
    # LOGIN BUTTON
    # --------------------------------------------------------

    login_button = st.button(
        "🔐 Login",
        use_container_width=True,
        type="primary",
    )

    if login_button:

        username_clean = username.strip()

        if not username_clean or not password:

            st.error(
                "Please enter both username and password."
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            return

        # ----------------------------------------------------
        # AUTHENTICATE
        # ----------------------------------------------------

        try:

            user = login(
                username_clean,
                password,
            )

        except Exception:

            st.error(
                "Unable to log in. Please try again."
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            return

        # ----------------------------------------------------
        # INVALID LOGIN
        # ----------------------------------------------------

        if not user:

            st.error(
                "Invalid username or password."
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            return

        # ----------------------------------------------------
        # LOGIN SUCCESSFUL
        # ----------------------------------------------------

        st.session_state.user = user
        st.session_state.remember_me = remember_me

        # ----------------------------------------------------
        # STUDENT COURSE
        # ----------------------------------------------------

        if user.get("role") == "student":

            courses = user.get(
                "courses",
                []
            )

            if len(courses) == 1:

                st.session_state.selected_course = (
                    courses[0]
                )

            else:

                st.session_state.selected_course = None

        # ----------------------------------------------------
        # REMEMBER ME ENABLED
        # ----------------------------------------------------

        if remember_me:

            try:

                token = create_login_token(
                    user
                )

                cookie_manager.set(
                    REMEMBER_COOKIE_NAME,
                    token,
                    max_age=REMEMBER_ME_DAYS * 24 * 60 * 60,
                    secure=True,
                    same_site="strict",
                )

            except Exception:

                st.warning(
                    "You are logged in, but Remember Me "
                    "could not be enabled on this browser."
                )

        # ----------------------------------------------------
        # REMEMBER ME NOT ENABLED
        # ----------------------------------------------------

        else:

            try:

                existing_token = cookie_manager.get(
                    REMEMBER_COOKIE_NAME
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

        # ----------------------------------------------------
        # GO TO PORTAL
        # ----------------------------------------------------

        st.rerun()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# LOGOUT
# ============================================================

def logout():

    """
    Log the user out of the current session and revoke the
    Remember Me token if one exists.
    """

    # --------------------------------------------------------
    # Revoke persistent login token
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Delete browser cookie
    # --------------------------------------------------------

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Clear session
    # --------------------------------------------------------

    st.session_state.user = None
    st.session_state.remember_me = False
    st.session_state.selected_course = None

    # --------------------------------------------------------
    # Return to login
    # --------------------------------------------------------

    st.rerun()


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================

def show_user_sidebar():

    user = st.session_state.get(
        "user"
    )

    if not user:
        return

    with st.sidebar:

        st.markdown("---")

        st.markdown(
            "### 👤 Current User"
        )

        username = user.get(
            "username",
            ""
        )

        role = user.get(
            "role",
            ""
        )

        st.write(
            f"**Username:** {username}"
        )

        st.write(
            f"**Role:** {role.title()}"
        )

        # ----------------------------------------------------
        # STUDENT COURSE SELECTION
        # ----------------------------------------------------

        if role == "student":

            courses = user.get(
                "courses",
                []
            )

            # ------------------------------------------------
            # Multiple courses
            # ------------------------------------------------

            if len(courses) > 1:

                current_course = (
                    st.session_state.selected_course
                )

                if current_course in courses:

                    default_index = courses.index(
                        current_course
                    )

                else:

                    default_index = 0

                selected_course = st.selectbox(
                    "Course",
                    courses,
                    index=default_index,
                    key="sidebar_course_selector",
                )

                st.session_state.selected_course = (
                    selected_course
                )

            # ------------------------------------------------
            # One course
            # ------------------------------------------------

            elif len(courses) == 1:

                st.session_state.selected_course = (
                    courses[0]
                )

                st.caption(
                    f"Course: {courses[0]}"
                )

        # ----------------------------------------------------
        # LOGOUT
        # ----------------------------------------------------

        st.markdown("")

        if st.button(
            "🚪 Logout",
            use_container_width=True,
        ):

            logout()


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # Initialize session state
    # --------------------------------------------------------

    initialize_session_state()

    # --------------------------------------------------------
    # Clean old remember-me tokens
    # --------------------------------------------------------

    cleanup_tokens_once()

    # --------------------------------------------------------
    # Attempt automatic login
    # --------------------------------------------------------

    if st.session_state.user is None:

        restore_remembered_login()

    # --------------------------------------------------------
    # Show login screen if not authenticated
    # --------------------------------------------------------

    if st.session_state.user is None:

        login_screen()

        return

    # --------------------------------------------------------
    # USER IS AUTHENTICATED
    # --------------------------------------------------------

    show_user_sidebar()

    user = st.session_state.user

    role = user.get(
        "role",
        ""
    ).lower()

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if role == "admin":

        admin_page()

    # --------------------------------------------------------
    # STUDENT
    # --------------------------------------------------------

    elif role == "student":

        student_page()

    # --------------------------------------------------------
    # INVALID ROLE
    # --------------------------------------------------------

    else:

        st.error(
            "Your account has an invalid role. "
            "Please contact the administrator."
        )

        if st.button(
            "🚪 Logout",
            type="primary",
        ):

            logout()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    main()
