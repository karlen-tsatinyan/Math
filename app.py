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
# ============================================================

@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


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


# ============================================================
# CLEANUP EXPIRED TOKENS
# ============================================================

def cleanup_tokens_once():

    if "tokens_cleaned" not in st.session_state:

        try:
            cleanup_expired_tokens()
        except Exception:
            # Do not prevent the application from opening
            # if cleanup encounters a database issue.
            pass

        st.session_state.tokens_cleaned = True


# ============================================================
# RESTORE LOGIN FROM COOKIE
# ============================================================

def restore_remembered_login():

    """
    Attempts to restore a previous login using the secure
    remember-me token stored in the browser cookie.

    The actual token is never stored in the database.
    The database stores only its SHA-256 hash.
    """

    if st.session_state.login_checked:
        return

    st.session_state.login_checked = True

    try:

        token = cookie_manager.get(REMEMBER_COOKIE_NAME)

        if not token:
            return

        user = login_from_token(token)

        if user:

            st.session_state.user = user
            st.session_state.remember_me = True

            # If the student has only one course, automatically
            # select it.
            if user.get("role") == "student":

                courses = user.get("courses", [])

                if len(courses) == 1:
                    st.session_state.selected_course = courses[0]

            return

        # Token was invalid or expired.
        # Remove it from the browser.
        try:
            cookie_manager.delete(REMEMBER_COOKIE_NAME)
        except Exception:
            pass

    except Exception:
        # Never prevent the login screen from loading because
        # of a cookie/database restoration issue.
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

    username = st.text_input(
        "Username",
        key="login_username",
    )

    password = st.text_input(
        "Password",
        type="password",
        key="login_password",
    )

    remember_me = st.checkbox(
        "Remember me on this device",
        value=False,
        key="login_remember_me",
    )

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

            return

        try:

            user = login(
                username_clean,
                password,
            )

        except Exception as e:

            st.error(
                "Unable to log in. Please try again."
            )

            return

        if not user:

            st.error(
                "Invalid username or password."
            )

            return

        # ----------------------------------------------------
        # LOGIN SUCCESSFUL
        # ----------------------------------------------------

        st.session_state.user = user
        st.session_state.remember_me = remember_me

        # ----------------------------------------------------
        # COURSE SELECTION
        # ----------------------------------------------------

        if user.get("role") == "student":

            courses = user.get("courses", [])

            if len(courses) == 1:

                st.session_state.selected_course = courses[0]

            else:

                st.session_state.selected_course = None

        # ----------------------------------------------------
        # REMEMBER ME
        # ----------------------------------------------------

        if remember_me:

            try:

                token = create_login_token(user)

                cookie_manager.set(
                    REMEMBER_COOKIE_NAME,
                    token,
                    expires_at=None,
                    max_age=REMEMBER_ME_DAYS * 24 * 60 * 60,
                    secure=True,
                    same_site="strict",
                )

            except Exception:

                # Login itself should still work even if the
                # persistent cookie cannot be created.
                st.warning(
                    "You are logged in, but Remember Me could "
                    "not be enabled on this browser."
                )

        else:

            # If the user previously had a remembered login,
            # revoke it when they intentionally log in without
            # Remember Me.
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
    Completely log out the current user.

    This removes the session and also revokes the persistent
    Remember Me token if one exists.
    """

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

        if token:

            revoke_login_token(token)

    except Exception:
        pass

    try:

        cookie_manager.delete(
            REMEMBER_COOKIE_NAME
        )

    except Exception:
        pass

    # Clear important session-state values.
    st.session_state.user = None
    st.session_state.remember_me = False
    st.session_state.selected_course = None

    # Force the application back to the login screen.
    st.rerun()


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================

def show_user_sidebar():

    user = st.session_state.get("user")

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
        # STUDENT COURSE
        # ----------------------------------------------------

        if role == "student":

            courses = user.get(
                "courses",
                []
            )

            if len(courses) > 1:

                selected_course = st.selectbox(
                    "Course",
                    courses,
                    index=(
                        courses.index(
                            st.session_state.selected_course
                        )
                        if st.session_state.selected_course
                        in courses
                        else 0
                    ),
                    key="sidebar_course_selector",
                )

                st.session_state.selected_course = (
                    selected_course
                )

            elif len(courses) == 1:

                st.session_state.selected_course = courses[0]

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

    initialize_session_state()

    # --------------------------------------------------------
    # CLEANUP OLD TOKENS
    # --------------------------------------------------------

    cleanup_tokens_once()

    # --------------------------------------------------------
    # TRY TO RESTORE REMEMBERED LOGIN
    # --------------------------------------------------------

    if st.session_state.user is None:

        restore_remembered_login()

    # --------------------------------------------------------
    # LOGIN SCREEN
    # --------------------------------------------------------

    if st.session_state.user is None:

        login_screen()

        return

    # --------------------------------------------------------
    # USER IS LOGGED IN
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
    # UNKNOWN ROLE
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
