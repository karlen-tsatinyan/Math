import streamlit as st

from database import (
    execute,
    execute_returning,
    query_dataframe
)

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
    
    
        code = st.text_input(
            "Student ID Code",
            key="add_code"
        )
    
        first = st.text_input(
            "First Name",
            key="add_first"
        )
    
        last = st.text_input(
            "Last Name",
            key="add_last"
        )
    
        grade = st.text_input(
            "Grade",
            key="add_grade"
        )
    
        subject = st.text_input(
            "Subject",
            key="add_subject"
        )
    
        email = st.text_input(
            "Email",
            key="add_email"
        )
    
        phone = st.text_input(
            "Phone",
            key="add_phone"
        )
    
    
        st.markdown("---")
        st.markdown("**Zoom Classroom Information**")
    
    
        zoom_link = st.text_input(
            "Zoom Link",
            key="add_zoom_link"
        )
    
        meeting_id = st.text_input(
            "Meeting ID",
            key="add_meeting_id"
        )
    
    
        st.markdown("---")
        st.markdown("**Portal Login Credentials**")
    
    
        username = st.text_input(
            "Username for Login",
            value=email.split("@")[0] if email else "",
            key="add_username"
        )
    
        password = st.text_input(
            "Initial Password",
            type="password",
            value="changeme123",
            key="add_password"
        )
    
    
    
        if st.button("Add Student"):
    
    
            if not first or not last:
    
                st.error(
                    "First name and last name are required."
                )
    
    
            elif not username or not password:
    
                st.error(
                    "Username and password are required for portal login."
                )
    
    
            else:
    
                # ===============================
                # DUPLICATE CHECK
                # PostgreSQL / Supabase
                # ===============================
                
                # Clean input values first
                clean_code = code.strip()
                clean_first = first.strip()
                clean_last = last.strip()
                clean_email = email.strip().lower()
                clean_username = username.strip().lower()
                
                
                # --------------------------------
                # Check Student ID Code
                # --------------------------------
                
                if clean_code:
                
                    existing_code = query_dataframe(
                        """
                        SELECT id
                        FROM students
                        WHERE student_code = %s
                        LIMIT 1
                        """,
                        (
                            clean_code,
                        )
                    )
                
                    if not existing_code.empty:
                
                        st.warning(
                            f"Student ID Code '{clean_code}' is already being used."
                        )
                
                        return
                
                
                # --------------------------------
                # Check Email
                # Allow siblings to share email
                # --------------------------------
                
                if clean_email:
                
                    existing_email = query_dataframe(
                        """
                        SELECT id
                        FROM students
                        WHERE LOWER(TRIM(email)) = %s
                        LIMIT 1
                        """,
                        (
                            clean_email,
                        )
                    )
                
                    # Email is allowed to be shared by siblings,
                    # so this is informational only.
                    if not existing_email.empty:
                
                        st.info(
                            "This email is already associated with another student. "
                            "That's okay if this is a family/shared parent email."
                        )
                
                
                # --------------------------------
                # Check Username
                # Username MUST be unique
                # --------------------------------
                
                existing_user = query_dataframe(
                    """
                    SELECT id
                    FROM users
                    WHERE LOWER(TRIM(username)) = %s
                    LIMIT 1
                    """,
                    (
                        clean_username,
                    )
                )
                
                if not existing_user.empty:
                
                    st.warning(
                        f"The username '{clean_username}' is already being used."
                    )
                
                    return
            
                existing_user = query_dataframe(
                    """
                    SELECT id
                    FROM users
                    WHERE username=%s
                    """,
                    (
                        username,
                    )
                )
            
                if len(existing_user) > 0:
                    st.warning(
                        "This username already exists."
                    )
                    return
    
    
                # ===============================
                # INSERT STUDENT
                # ===============================
    
                try:
    
                    row = execute_returning(
                        """
                        INSERT INTO students
                        (
                            student_code,
                            first_name,
                            last_name,
                            grade,
                            subject,
                            email,
                            phone,
                            zoom_link,
                            meeting_id
                        )
                        VALUES
                        (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING id
                        """,
                        (
                            clean_code,
                            clean_first,
                            clean_last,
                            grade.strip(),
                            subject.strip(),
                            clean_email,
                            phone.strip(),
                            zoom_link.strip(),
                            meeting_id.strip()
                        )
                    )
    
    
                    new_student_id = int(row[0])
    
    
    
                    # ===============================
                    # CREATE STUDENT LOGIN
                    # ===============================
    
    
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
                        (%s,%s,'student',%s)
                        """,
                        (
                            clean_username,
                            password,
                            new_student_id
                        )
                    )
    
    
    
                    if "student_version" not in st.session_state:
    
                        st.session_state.student_version = 0
    
    
    
                    st.session_state.student_version += 1
    
    
                    st.cache_data.clear()
    
                    st.cache_resource.clear()
    
    
    
                    st.success(
    
                        f"Student added successfully! "
                        f"Linked Student ID is {new_student_id}."
    
                    )
    
    
                    st.rerun()
    
    
    
                except Exception as e:
    
    
                    st.error(
    
                        f"Error adding student: {e}"
    
                    )

    with tab2:

        st.subheader("Current Students")

        if "student_version" not in st.session_state:
            st.session_state.student_version = 0

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
            ORDER BY id DESC
            """
        )

        if not students.empty:
            # Safely combine first and last name for visibility
            students["Student Name"] = students["first_name"].fillna("") + " " + students["last_name"].fillna("")
            
            display_df = students[[
                "id",
                "student_code",
                "Student Name",
                "grade",
                "subject",
                "email",
                "phone"
            ]].rename(columns={
                "id": "ID",
                "student_code": "Student Code",
                "grade": "Grade",
                "subject": "Subject",
                "email": "Email",
                "phone": "Phone"
            })

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No students found in the database.")

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
                phone,
                zoom_link,
                meeting_id
            FROM students
            ORDER BY id DESC
            """
        )

        if not edit_students.empty:
            edit_students["display_name"] = edit_students["first_name"].fillna("") + " " + edit_students["last_name"].fillna("") + " (Code: " + edit_students["student_code"].fillna("N/A") + ")"
            
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
                
                st.markdown("---")
                st.markdown("**Zoom Classroom Information**")
                e_zoom = st.text_input("Zoom Link", value=str(student_row["zoom_link"]) if student_row["zoom_link"] and str(student_row["zoom_link"]) != "nan" else "")
                e_meeting = st.text_input("Meeting ID", value=str(student_row["meeting_id"]) if student_row["meeting_id"] and str(student_row["meeting_id"]) != "nan" else "")

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
                                    phone = %s,
                                    zoom_link = %s,
                                    meeting_id = %s
                                WHERE id = %s
                                """,
                                (e_code, e_first, e_last, e_grade, e_subject, e_email, e_phone, e_zoom, e_meeting, student_id)
                            )
                            
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            
                            st.success("Student information updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating student: {e}")
        else:
            st.info("No students available to edit.")
