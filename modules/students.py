import streamlit as st
from database import execute, query_dataframe


def student_management():

    st.header("Student Management")

    tab1, tab2 = st.tabs(
        [
            "Add Student",
            "Student List"
        ]
    )

    with tab1:

        st.subheader("Create Student Record")

        code = st.text_input("Student ID Code")
        first = st.text_input("First Name")
        last = st.text_input("Last Name")
        grade = st.text_input("Grade")
        subject = st.text_input("Subject")
        email = st.text_input("Email")
        phone = st.text_input("Phone")

        if st.button("Add Student"):

            execute(
                """
                INSERT INTO students
                (
                    student_code,
                    first_name,
                    last_name,
                    grade,
                    subject,
                    email,
                    phone
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    code,
                    first,
                    last,
                    grade,
                    subject,
                    email,
                    phone
                )
            )

            st.success("Student added successfully")

    with tab2:

        st.subheader("Current Students")

        students = query_dataframe(
            """
            SELECT
                id,
                student_code,
                first_name,
                last_name,
                grade,
                subject,
                email,
                phone
            FROM students
            ORDER BY last_name
            """
        )

        st.dataframe(
            students,
            use_container_width=True
        )

    st.divider()

    st.subheader("Create Student Login")

    login_students = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        ORDER BY last_name
        """
    )

    if len(login_students) > 0:

        selected_student = st.selectbox(
            "Student",
            login_students["name"],
            key="create_login_student"
        )

        student_id = int(
            login_students[
                login_students["name"] == selected_student
            ]["id"].iloc[0]
        )

        username = st.text_input(
            "Username",
            key="new_student_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="new_student_password"
        )

        if st.button("Create Student Account"):

            execute(
                """
                INSERT INTO users
                (
                    username,
                    password,
                    role,
                    student_id
                )
                VALUES
                (%s, %s, %s, %s)
                """,
                (
                    username,
                    password,
                    "student",
                    student_id
                )
            )

            st.success("Student login created.")
