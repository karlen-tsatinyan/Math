import streamlit as st
from database import execute, query_dataframe


def student_management():

    st.header("Student Management")

    tab1, tab2, tab3 = st.tabs(
        [
            "Add Student",
            "Student List",
            "Edit Student"
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
        
        st.markdown("---")
        st.markdown("**Portal Login Credentials**")
        username = st.text_input("Username for Login", value=email.split("@")[0] if email else "")
        password = st.text_input("Initial Password", type="password", value="changeme123")
    
        if st.button("Add Student"):
            if not first or not last:
                st.error("First name and last name are required.")
            else:
                try:
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
                        
                        if username and password:
                            execute(
                                """
                                INSERT INTO users (username, password, role, student_id)
                                VALUES (%s, %s, 'student', %s)
                                """,
                                (username, password, new_student_id)
                            )
                        
                        st.success(f"Student added successfully! Linked Student ID is {new_student_id}.")
                        st.cache_data.clear()
                        st.cache_resource.clear()
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

    with tab3:
        st.subheader("Edit Student Information")

        edit_students = query_dataframe(
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

        if not edit_students.empty:
            edit_students["display_name"] = edit_students["first_name"] + " " + edit_students["last_name"] + " (Code: " + edit_students["student_code"].fillna("N/A") + ")"
            
            selected_edit_name = st.selectbox(
                "Select Student to Edit",
                edit_students["display_name"],
                key="edit_student_selectbox"
            )

            student_row = edit_students[edit_students["display_name"] == selected_edit_name].iloc[0]
            student_id = int(student_row["id"])

            with st.form("edit_student_form"):
                e_code = st.text_input("Student ID Code", value=str(student_row["student_code"]) if student_row["student_code"] else "")
                e_first = st.text_input("First Name", value=str(student_row["first_name"]) if student_row["first_name"] else "")
                e_last = st.text_input("Last Name", value=str(student_row["last_name"]) if student_row["last_name"] else "")
                e_grade = st.text_input("Grade", value=str(student_row["grade"]) if student_row["grade"] else "")
                e_subject = st.text_input("Subject", value=str(student_row["subject"]) if student_row["subject"] else "")
                e_email = st.text_input("Email", value=str(student_row["email"]) if student_row["email"] else "")
                e_phone = st.text_input("Phone", value=str(student_row["phone"]) if student_row["phone"] else "")

                submit_edit = st.form_submit_button("Update Student Record")

                if submit_edit:
                    if not e_first or not e_last:
                        st.error("First name and last name are required.")
                    else:
                        try:
                            execute(
                                """
                                UPDATE students
                                SET student_code = %s,
                                    first_name = %s,
                                    last_name = %s,
                                    grade = %s,
                                    subject = %s,
                                    email = %s,
                                    phone = %s
                                WHERE id = %s
                                """,
                                (e_code, e_first, e_last, e_grade, e_subject, e_email, e_phone, student_id)
                            )
                            st.success("Student information updated successfully!")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating student: {e}")
        else:
            st.info("No students available to edit.")

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
                st.cache_data.clear()
                st.cache_resource.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error creating student account: {e}")
