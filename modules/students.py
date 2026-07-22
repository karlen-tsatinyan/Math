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
        
        # Optional: Add fields to automatically provision their portal login credentials here
        st.markdown("---")
        st.markdown("**Portal Login Credentials**")
        username = st.text_input("Username for Login", value=email.split("@")[0] if email else "")
        password = st.text_input("Initial Password", type="password", value="changeme123")
    
        if st.button("Add Student"):
            if not first or not last:
                st.error("First name and last name are required.")
            else:
                try:
                    # 1. Insert student and cleanly retrieve the newly generated primary key ID in PostgreSQL
                    res = query_dataframe(
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
                        RETURNING id
                        """,
                        (code, first, last, grade, subject, email, phone)
                    )
                    
                    if not res.empty:
                        new_student_id = int(res.iloc[0]["id"])
                        
                        # 2. Automatically create the matching user login record linked by student_id
                        if username and password:
                            execute(
                                """
                                INSERT INTO users (username, password, role, student_id)
                                VALUES (%s, %s, 'student', %s)
                                """,
                                (username, password, new_student_id)
                            )
                        
                        st.success(f"Student added successfully! Linked Student ID is {new_student_id}.")
                        st.rerun()
                    else:
                        st.error("Failed to retrieve new student ID.")
                except Exception as e:
                    st.error(f"Error adding student: {e}")

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
            try:
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
                st.rerun()
            except Exception as e:
                st.error(f"Error creating student account: {e}")
