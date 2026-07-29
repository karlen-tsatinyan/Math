import streamlit as st

from database import (
    execute,
    execute_returning,
    query_dataframe
)


def student_management():

    st.header("Student Management")

    # ==========================================================
    # TABS
    # ==========================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Add Student",
            "Active Students",
            "Archived Students",
            "Edit Student"
        ]
    )

    # ==========================================================
    # TAB 1 — ADD STUDENT
    # ==========================================================

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

        # ------------------------------------------------------
        # ZOOM
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # LOGIN
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # PARENT PIN
        # ------------------------------------------------------

        parent_pin = st.text_input(
            "Parent PIN",
            type="password",
            value="",
            key="add_parent_pin",
            help=(
                "PIN used by the parent to access "
                "confidential financial information."
            )
        )

        # ------------------------------------------------------
        # ADD STUDENT BUTTON
        # ------------------------------------------------------

        if st.button(
            "Add Student",
            type="primary",
            key="add_student_button"
        ):

            if not first.strip() or not last.strip():

                st.error(
                    "First name and last name are required."
                )

            elif not username.strip() or not password.strip():

                st.error(
                    "Username and password are required "
                    "for portal login."
                )

            else:

                # ==================================================
                # CLEAN INPUT
                # ==================================================

                clean_code = code.strip()
                clean_first = first.strip()
                clean_last = last.strip()
                clean_email = email.strip().lower()
                clean_username = username.strip().lower()
                clean_grade = grade.strip()
                clean_subject = subject.strip()
                clean_phone = phone.strip()
                clean_zoom = zoom_link.strip()
                clean_meeting = meeting_id.strip()
                clean_parent_pin = parent_pin.strip()

                # ==================================================
                # STUDENT CODE DUPLICATE CHECK
                # ==================================================

                if clean_code:

                    existing_code = query_dataframe(
                        """
                        SELECT id
                        FROM students
                        WHERE student_code = %s
                        LIMIT 1
                        """,
                        (clean_code,)
                    )

                    if not existing_code.empty:

                        st.warning(
                            f"Student ID Code '{clean_code}' "
                            "is already being used."
                        )

                        return

                # ==================================================
                # USERNAME + EMAIL DUPLICATE CHECK
                #
                # Both must match the SAME existing account
                # before we block the new student.
                # ==================================================

                if clean_email:

                    existing_user = query_dataframe(
                        """
                        SELECT s.id
                        FROM users u
                        JOIN students s
                            ON u.student_id = s.id
                        WHERE LOWER(TRIM(u.username)) = %s
                          AND LOWER(TRIM(s.email)) = %s
                        LIMIT 1
                        """,
                        (
                            clean_username,
                            clean_email
                        )
                    )

                    if not existing_user.empty:

                        st.warning(
                            "A student account with this "
                            "username and email already exists."
                        )

                        return

                # ==================================================
                # INSERT STUDENT
                # ==================================================

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
                            meeting_id,
                            parent_pin,
                            archived
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            0
                        )
                        RETURNING id
                        """,
                        (
                            clean_code,
                            clean_first,
                            clean_last,
                            clean_grade,
                            clean_subject,
                            clean_email,
                            clean_phone,
                            clean_zoom,
                            clean_meeting,
                            clean_parent_pin
                        )
                    )

                    new_student_id = int(row[0])

                    # ==================================================
                    # CREATE STUDENT LOGIN
                    # ==================================================

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
                        (
                            %s,
                            %s,
                            'student',
                            %s
                        )
                        """,
                        (
                            clean_username,
                            password,
                            new_student_id
                        )
                    )

                    # ==================================================
                    # CLEAR CACHE
                    # ==================================================

                    st.cache_data.clear()

                    if hasattr(st, "cache_resource"):
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

    # ==========================================================
    # TAB 2 — ACTIVE STUDENTS
    # ==========================================================

    with tab2:

        st.subheader("Active Students")

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
            WHERE COALESCE(archived, 0) = 0
            ORDER BY id DESC
            """
        )

        if not students.empty:

            students["Student Name"] = (
                students["first_name"].fillna("")
                + " "
                + students["last_name"].fillna("")
            ).str.strip()

            display_df = students[
                [
                    "id",
                    "student_code",
                    "Student Name",
                    "grade",
                    "subject",
                    "email",
                    "phone"
                ]
            ].rename(
                columns={
                    "id": "ID",
                    "student_code": "Student Code",
                    "grade": "Grade",
                    "subject": "Subject",
                    "email": "Email",
                    "phone": "Phone"
                }
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            # --------------------------------------------------
            # ARCHIVE STUDENT
            # --------------------------------------------------

            st.subheader("Archive Student")

            student_options = students["id"].tolist()

            selected_archive_id = st.selectbox(
                "Select Student to Archive",
                student_options,
                format_func=lambda x: (
                    f"{students.loc[students['id'] == x, 'Student Name'].iloc[0]} "
                    f"(ID: {x})"
                ),
                key="archive_student_select"
            )

            selected_archive_row = students[
                students["id"] == selected_archive_id
            ].iloc[0]

            st.info(
                f"You are about to archive "
                f"**{selected_archive_row['Student Name']}**. "
                "Their homework, grades, attendance, sessions, "
                "payments, login, and other history will remain "
                "in the database."
            )

            if st.button(
                "📦 Archive Student",
                type="secondary",
                key="archive_student_button"
            ):

                try:

                    execute(
                        """
                        UPDATE students
                        SET archived = 1
                        WHERE id = %s
                        """,
                        (int(selected_archive_id),)
                    )

                    st.cache_data.clear()

                    if hasattr(st, "cache_resource"):
                        st.cache_resource.clear()

                    st.success(
                        f"{selected_archive_row['Student Name']} "
                        "has been archived."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Error archiving student: {e}"
                    )

        else:

            st.info(
                "No active students found."
            )

    # ==========================================================
    # TAB 3 — ARCHIVED STUDENTS
    # ==========================================================

    with tab3:

        st.subheader("Archived Students")

        archived_students = query_dataframe(
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
            WHERE archived = 1
            ORDER BY id DESC
            """
        )

        if not archived_students.empty:

            archived_students["Student Name"] = (
                archived_students["first_name"].fillna("")
                + " "
                + archived_students["last_name"].fillna("")
            ).str.strip()

            display_archived = archived_students[
                [
                    "id",
                    "student_code",
                    "Student Name",
                    "grade",
                    "subject",
                    "email",
                    "phone"
                ]
            ].rename(
                columns={
                    "id": "ID",
                    "student_code": "Student Code",
                    "grade": "Grade",
                    "subject": "Subject",
                    "email": "Email",
                    "phone": "Phone"
                }
            )

            st.dataframe(
                display_archived,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            # --------------------------------------------------
            # RESTORE STUDENT
            # --------------------------------------------------

            st.subheader("Restore Student")

            archived_options = archived_students["id"].tolist()

            selected_restore_id = st.selectbox(
                "Select Student to Restore",
                archived_options,
                format_func=lambda x: (
                    f"{archived_students.loc[archived_students['id'] == x, 'Student Name'].iloc[0]} "
                    f"(ID: {x})"
                ),
                key="restore_student_select"
            )

            selected_restore_row = archived_students[
                archived_students["id"] == selected_restore_id
            ].iloc[0]

            if st.button(
                "♻️ Restore Student",
                type="primary",
                key="restore_student_button"
            ):

                try:

                    execute(
                        """
                        UPDATE students
                        SET archived = 0
                        WHERE id = %s
                        """,
                        (int(selected_restore_id),)
                    )

                    st.cache_data.clear()

                    if hasattr(st, "cache_resource"):
                        st.cache_resource.clear()

                    st.success(
                        f"{selected_restore_row['Student Name']} "
                        "has been restored."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Error restoring student: {e}"
                    )

        else:

            st.info(
                "There are currently no archived students."
            )

    # ==========================================================
    # TAB 4 — EDIT STUDENT
    # ==========================================================

    with tab4:

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
                meeting_id,
                parent_pin
            FROM students
            WHERE COALESCE(archived, 0) = 0
            ORDER BY id DESC
            """
        )

        if not edit_students.empty:

            edit_students["display_name"] = (
                edit_students["first_name"].fillna("")
                + " "
                + edit_students["last_name"].fillna("")
                + " (Code: "
                + edit_students["student_code"].fillna("N/A")
                + ")"
            )

            selected_edit_id = st.selectbox(
                "Select Student to Edit",
                edit_students["id"].tolist(),
                format_func=lambda x: (
                    edit_students.loc[
                        edit_students["id"] == x,
                        "display_name"
                    ].iloc[0]
                ),
                key="edit_student_selectbox"
            )

            student_row = edit_students[
                edit_students["id"] == selected_edit_id
            ].iloc[0]

            student_id = int(student_row["id"])

            # --------------------------------------------------
            # EDIT FORM
            # --------------------------------------------------

            with st.form(
                f"edit_student_form_{student_id}"
            ):

                e_code = st.text_input(
                    "Student ID Code",
                    value=(
                        str(student_row["student_code"])
                        if student_row["student_code"]
                        else ""
                    )
                )

                e_first = st.text_input(
                    "First Name",
                    value=(
                        str(student_row["first_name"])
                        if student_row["first_name"]
                        else ""
                    )
                )

                e_last = st.text_input(
                    "Last Name",
                    value=(
                        str(student_row["last_name"])
                        if student_row["last_name"]
                        else ""
                    )
                )

                e_grade = st.text_input(
                    "Grade",
                    value=(
                        str(student_row["grade"])
                        if student_row["grade"]
                        else ""
                    )
                )

                e_subject = st.text_input(
                    "Subject",
                    value=(
                        str(student_row["subject"])
                        if student_row["subject"]
                        else ""
                    )
                )

                e_email = st.text_input(
                    "Email",
                    value=(
                        str(student_row["email"])
                        if student_row["email"]
                        else ""
                    )
                )

                e_phone = st.text_input(
                    "Phone",
                    value=(
                        str(student_row["phone"])
                        if student_row["phone"]
                        else ""
                    )
                )

                # --------------------------------------------------
                # ZOOM
                # --------------------------------------------------

                st.markdown("---")
                st.markdown(
                    "**Zoom Classroom Information**"
                )

                e_zoom = st.text_input(
                    "Zoom Link",
                    value=(
                        str(student_row["zoom_link"])
                        if student_row["zoom_link"]
                        and str(student_row["zoom_link"]) != "nan"
                        else ""
                    )
                )

                e_meeting = st.text_input(
                    "Meeting ID",
                    value=(
                        str(student_row["meeting_id"])
                        if student_row["meeting_id"]
                        and str(student_row["meeting_id"]) != "nan"
                        else ""
                    )
                )

                # --------------------------------------------------
                # LOGIN
                # --------------------------------------------------

                st.markdown("---")
                st.markdown(
                    "**Portal Login Credentials**"
                )

                e_password = st.text_input(
                    "New Password "
                    "(leave blank to keep current)",
                    type="password",
                    key=f"edit_password_{student_id}",
                    placeholder=(
                        "Enter new password if changing"
                    )
                )

                # --------------------------------------------------
                # PARENT PIN
                # --------------------------------------------------

                e_parent_pin = st.text_input(
                    "Parent PIN",
                    type="password",
                    value=(
                        str(student_row["parent_pin"])
                        if student_row["parent_pin"]
                        and str(student_row["parent_pin"]) != "nan"
                        else ""
                    ),
                    key=f"edit_parent_pin_{student_id}",
                    help=(
                        "PIN used by the parent to access "
                        "confidential financial information."
                    )
                )

                submit_edit = st.form_submit_button(
                    "Update Student Record"
                )

                if submit_edit:

                    if not e_first.strip() or not e_last.strip():

                        st.error(
                            "First name and last name are required."
                        )

                    else:

                        try:

                            # ======================================
                            # UPDATE STUDENT INFORMATION
                            # ======================================

                            execute(
                                """
                                UPDATE students
                                SET
                                    student_code = %s,
                                    first_name = %s,
                                    last_name = %s,
                                    grade = %s,
                                    subject = %s,
                                    email = %s,
                                    phone = %s,
                                    zoom_link = %s,
                                    meeting_id = %s,
                                    parent_pin = %s
                                WHERE id = %s
                                """,
                                (
                                    e_code.strip(),
                                    e_first.strip(),
                                    e_last.strip(),
                                    e_grade.strip(),
                                    e_subject.strip(),
                                    e_email.strip().lower(),
                                    e_phone.strip(),
                                    e_zoom.strip(),
                                    e_meeting.strip(),
                                    e_parent_pin.strip(),
                                    student_id
                                )
                            )

                            # ======================================
                            # UPDATE PASSWORD ONLY IF ENTERED
                            # ======================================

                            if e_password.strip():

                                execute(
                                    """
                                    UPDATE users
                                    SET password = %s
                                    WHERE student_id = %s
                                    """,
                                    (
                                        e_password.strip(),
                                        student_id
                                    )
                                )

                            # ======================================
                            # CLEAR CACHE
                            # ======================================

                            st.cache_data.clear()

                            if hasattr(st, "cache_resource"):
                                st.cache_resource.clear()

                            st.success(
                                "Student information updated successfully!"
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Error updating student: {e}"
                            )

        else:

            st.info(
                "No active students available to edit."
            )
