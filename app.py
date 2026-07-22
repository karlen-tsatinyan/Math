import streamlit as st

from authentication import login
from pages.admin import admin_page
from pages.student import student_page

st.markdown(
    """
    <style>
        /* Hide the status toast / running indicator completely */
        [data-testid="stStatusWidget"] {
            display: none !important;
        }
        /* Hide the small floating running man / spinner on top right */
        header [data-testid="stDecoration"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(
    page_title="Advanced Math Tutoring Portal",
    layout="wide"
)


if "user" not in st.session_state:
    st.session_state.user = None


def login_screen():
    st.title("Advanced Math Tutoring Portal")

    username = st.text_input(
        "Username",
        key="username_login"
    )

    password = st.text_input(
        "Password",
        type="password",
        key="password_login"
    )

    if st.button("Login"):
        user = login(
            username,
            password
        )

        if user:
            st.session_state.user = user
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Incorrect username/password")


def main():
    if st.session_state.user is None:
        login_screen()
    else:
        user = st.session_state.user

        st.sidebar.write(
            f"Logged in: {user['username']}"
        )

        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()

        if user["role"] == "admin":
            admin_page()
        else:
            student_page()


if __name__ == "__main__":
    main()
