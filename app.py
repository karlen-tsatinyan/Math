import time

import streamlit as st
from streamlit_cookies_controller import CookieController

from authentication import (
    login,
    create_login_token,
    login_from_token,
    revoke_login_token,
    cleanup_expired_tokens,
)

from pages.student import student_page
from pages.admin import admin_page


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    page_icon="📚",
    layout="wide",
)

st.set_option(
    "client.showErrorDetails",
    False,
)


# ==========================================================
# REMEMBER ME SETTINGS
# ==========================================================

REMEMBER_COOKIE_NAME = "advanced_math_remember_me"

REMEMBER_ME_DAYS = 30

REMEMBER_ME_SECONDS = (
    REMEMBER_ME_DAYS
    * 24
    * 60
    * 60
)


# ==========================================================
# COOKIE CONTROLLER
#
# streamlit-cookies-controller is used for the persistent
# browser cookie.
#
# Do NOT use extra-streamlit-components here.
# ==========================================================

if "cookie_manager" not in st.session_state:

    st.session_state.cookie_manager = CookieController()


cookie_manager = st.session_state.cookie_manager


# ==========================================================
# CSS
# ==========================================================

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
       COURSE SELECTION
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
    unsafe_allow_html=True,
)


# ==========================================================
# SESSION STATE
# ==========================================================

if "user" not in st.session_state:
    st.session_state.user = None


if "selected_course" not in st.session_state:
    st.session_state.selected_course = None


if "remember_cookie_checked" not in st.session_state:
    st.session_state.remember_cookie_checked = False


if "remember_tokens_cleaned" not in st.session_state:
    st.session_state.remember_tokens_cleaned = False


# ==========================================================
# COOKIE OPERATION HELPERS
# ==========================================================

def set_remember_cookie(token):
    """
    Store the Remember-Me token in the browser.

    The token itself is stored in the browser.
    Only its SHA-256 hash is stored in the database.
    """

    if not token:
        return False

    try:

        cookie_manager.set(
            REMEMBER_COOKIE_NAME,
            token,
            path="/",
            max_age=REMEMBER_ME_SECONDS,
            secure=True,
            same_site="strict",
        )

        # Give the browser component time to process
        # the cookie operation.
        time.sleep(1)

        return True

    except Exception as e:

        print(
            f"Remember-Me cookie set error: {e}"
        )

        return False


def delete_remember_cookie():
    """
    Remove the Remember-Me cookie from the browser.
    """

    try:

        cookie_manager.remove(
            REMEMBER_COOKIE_NAME
        )

        time.sleep(0.5)

        return True

    except Exception as e:

        print(
            f"Remember-Me cookie removal error: {e}"
        )

        return False


def get_remember_cookie():
    """
    Read the Remember-Me token from the browser.
    """

    try:

        token = cookie_manager.get(
            REMEMBER_COOKIE_NAME
        )

        return token

    except Exception as e:

        print(
            f"Remember-Me cookie read error: {e}"
        )

        return None


# ==========================================================
# CLEAN OLD TOKENS
# ==========================================================

def cleanup_remember_tokens():

    if st.session_state.remember_tokens_cleaned:
        return

    try:

        cleanup_expired_tokens()

    except Exception:

        # Cleanup must never stop the application.
        pass

    st.session_state.remember_tokens_cleaned = True


# ==========================================================
# RESTORE REMEMBERED LOGIN
# ==========================================================

def restore_remembered_login():

    """
    Restore the user from the persistent browser cookie.

    If a valid Remember-Me token exists:

        browser cookie
              ↓
        login_tokens
              ↓
        user
              ↓
        Streamlit session

    """

    # ------------------------------------------------------
    # Already checked during this Streamlit session
    # ------------------------------------------------------

    if st.session_state.remember_cookie_checked:

        return True


    # ------------------------------------------------------
    # Read browser cookie
    # ------------------------------------------------------

    token = get_remember_cookie()


    # ======================================================
    # NO COOKIE
    # ======================================================

    if not token:

        st.session_state.remember_cookie_checked = True

        return True


    # ======================================================
    # VALIDATE TOKEN
    # ======================================================

    try:

        user = login_from_token(
            token
        )

    except Exception as e:

        print(
            f"Remember-Me restore error: {e}"
        )

        user = None


    # ======================================================
    # VALID TOKEN
    # ======================================================

    if user:

        st.session_state.user = user

        st.session_state.selected_course = (
            user.get("selected_course")
        )

        st.session_state.remember_cookie_checked = True

        return True


    # ======================================================
    # INVALID / EXPIRED / REVOKED TOKEN
    # ======================================================

    try:

        revoke_login_token(
            token
        )

    except Exception:

        pass


    delete_remember_cookie()


    st.session_state.remember_cookie_checked = True

    return True


# ==========================================================
# LOGIN SCREEN
# ==========================================================

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


        # --------------------------------------------------
        # REMEMBER ME
        # --------------------------------------------------

        remember_me = st.checkbox(
            "Remember me on this device",
            value=False,
        )


        submitted = st.form_submit_button(
            "Login",
            type="primary",
        )


        if not submitted:

            return


        # ==================================================
        # VALIDATE INPUT
        # ==================================================

        if not username.strip() or not password:

            st.error(
                "Please enter your username and password."
            )

            return


        # ==================================================
        # NORMAL LOGIN
        # ==================================================

        with st.spinner(
            "Signing you in..."
        ):

            try:

                user = login(
                    username,
                    password,
                )

            except Exception as e:

                print(
                    f"Login error: {e}"
                )

                user = None


        # ==================================================
        # INVALID LOGIN
        # ==================================================

        if not user:

            st.error(
                "Incorrect username or password."
            )

            return


        # ==================================================
        # SAVE USER
        # ==================================================

        st.session_state.user = user

        st.session_state.selected_course = (
            user.get("selected_course")
        )


        # ==================================================
        # REMEMBER ME SELECTED
        # ==================================================

        if remember_me:

            try:

                # ------------------------------------------
                # Create secure database token
                # ------------------------------------------

                token = create_login_token(
                    user
                )


                if not token:

                    raise RuntimeError(
                        "Could not create login token."
                    )


                # ------------------------------------------
                # Store token in browser
                # ------------------------------------------

                cookie_saved = set_remember_cookie(
                    token
                )


                if not cookie_saved:

                    raise RuntimeError(
                        "Browser cookie could not be set."
                    )


            except Exception as e:

                # ------------------------------------------
                # Normal login still succeeds.
                #
                # Only persistent Remember Me failed.
                # ------------------------------------------

                print(
                    f"Remember-Me login error: {e}"
                )

                st.warning(
                    "You are logged in, but "
                    "Remember Me could not be enabled "
                    "on this browser."
                )


        else:

            # ==================================================
            # REMEMBER ME NOT SELECTED
            #
            # Remove an old Remember-Me cookie if one exists.
            # ==================================================

            try:

                old_token = get_remember_cookie()


                if old_token:

                    try:

                        revoke_login_token(
                            old_token
                        )

                    except Exception:

                        pass


                delete_remember_cookie()

            except Exception:

                pass


        # ==================================================
        # LOGIN SUCCESS
        # ==================================================

        st.success(
            "Welcome!"
        )


        st.session_state.remember_cookie_checked = True


        time.sleep(0.5)

        st.rerun()


# ==========================================================
# COURSE SELECTION SCREEN
# ==========================================================

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
            key="logout_no_course",
        ):

            logout_user()


        return


    # ======================================================
    # ONE COURSE
    # ======================================================

    if len(courses) == 1:

        st.session_state.selected_course = (
            courses[0]
        )

        st.rerun()

        return


    # ======================================================
    # MULTIPLE COURSES
    # ======================================================

    st.markdown(
        '<h2 class="course-title">'
        '📚 Choose Your Course'
        '</h2>',
        unsafe_allow_html=True,
    )


    st.markdown(
        '<p class="course-subtitle">'
        'Please select the course you would like to enter.'
        '</p>',
        unsafe_allow_html=True,
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
                key=f"course_select_{index}",
            ):

                st.session_state.selected_course = (
                    course
                )


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
        key="course_selection_logout",
    ):

        logout_user()


# ==========================================================
# SIDEBAR FOOTER
# ==========================================================

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


    # ======================================================
    # REFRESH
    # ======================================================

    with col1:

        if st.button(
            "🔄 Refresh",
            use_container_width=True,
            key="global_refresh",
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


    # ======================================================
    # LOGOUT
    # ======================================================

    with col2:

        if st.button(
            "Logout",
            use_container_width=True,
            key="global_logout",
        ):

            logout_user()


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


# ==========================================================
# LOGOUT
# ==========================================================

def logout_user():

    """
    Logout the current browser/device.

    Only the Remember-Me token belonging to this browser
    is revoked.

    Other browsers/devices remain logged in.
    """


    # ======================================================
    # GET CURRENT BROWSER TOKEN
    # ======================================================

    token = get_remember_cookie()


    # ======================================================
    # REVOKE CURRENT TOKEN
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

    delete_remember_cookie()


    # ======================================================
    # CLEAR SESSION
    # ======================================================

    st.session_state.user = None

    st.session_state.selected_course = None

    st.session_state.remember_cookie_checked = False


    # ======================================================
    # CLEAR APPLICATION CACHE
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


# ==========================================================
# MAIN
# ==========================================================

def main():

    # ======================================================
    # CLEAN EXPIRED TOKENS
    # ======================================================

    cleanup_remember_tokens()


    # ======================================================
    # TRY REMEMBERED LOGIN
    # ======================================================

    if st.session_state.user is None:

        restore_finished = (
            restore_remembered_login()
        )

        if not restore_finished:

            return


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
    # MULTIPLE COURSES
    # ======================================================

    if (
        len(courses) > 1
        and not selected_course
    ):

        course_selection_screen()

        return


    # ======================================================
    # ONE COURSE
    # ======================================================

    if (
        len(courses) == 1
        and not selected_course
    ):

        st.session_state.selected_course = (
            courses[0]
        )


        user["selected_course"] = (
            courses[0]
        )


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
    # STUDENT PORTAL
    # ======================================================

    user["selected_course"] = (
        selected_course
    )


    st.session_state.user = user


    student_page()


    # ======================================================
    # SIDEBAR
    # ======================================================

    sidebar_footer(user)


# ==========================================================
# START APPLICATION
# ==========================================================

if __name__ == "__main__":

    main()
