import streamlit as st

from database import (
    execute,
    execute_returning,
    query_dataframe
)


# ==========================================================
# COURSE OPTIONS
# ==========================================================

COURSE_OPTIONS = [
    "Algebra",
    "Geometry",
    "Pre-Algebra",
    "Precalculus",
    "Trigonometry",
    "Calculus",
    "Algebra II"
]


# ==========================================================
# COURSE HELPERS
# ==========================================================

def parse_courses(subject):
    """
    Convert the existing subject field into a clean list.

    Example:

        "Algebra, Geometry, Algebra II"

    becomes:

        ["Algebra", "Geometry", "Algebra II"]

    Duplicate courses are removed while preserving order.
    """

    if subject is None:
        return []

    text = str(subject).strip()

    if not text:
        return []

    if text.lower() in ["nan", "none"]:
        return []

    raw_courses = text.split(",")

    courses = []

    for course in raw_courses:

        clean_course = course.strip()

        if not clean_course:
            continue

        # Remove duplicate courses case-insensitively
        if any(
            clean_course.lower() == existing.lower()
            for existing in courses
        ):
            continue

        courses.append(clean_course)

    return courses


def courses_to_subject(courses):
    """
    Convert selected courses into the existing
    students.subject database format.
    """

    cleaned = []

    for course in courses:

        if course is None:
            continue

        clean_course = str(course).strip()

        if not clean_course:
            continue

        if any(
            clean_course.lower() == existing.lower()
            for existing in cleaned
        ):
            continue

        cleaned.append(clean_course)

    return ", ".join(cleaned)


# ==========================================================
# STUDENT MANAGEMENT
# ==========================================================

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

        # ------------------------------------------------------
        # COURSES
        # ------------------------------------------------------

        st.markdown("---")

        st.markdown("**Courses**")

        st.caption(
            "Select all courses this student is enrolled in."
        )

        add_course_columns = st.columns(2)

        add_courses = []

        for index, course in enumerate(COURSE_OPTIONS):

            with add_course_columns[index % 2]:

                selected = st.checkbox(
                    course,
                    key=f"add_course_{course}"
                )

                if selected:
                    add_courses.append(course)

        # ------------------------------------------------------
        # OTHER / CUSTOM COURSE
        # ------------------------------------------------------

        add_other_course = st.text_input(
            "Other Course (optional)",
            key="add_other_course",
            placeholder="Example: Statistics"
        )

        if add_other_course.strip():

            for course in add_other_course.split(","):

                clean_course = course.strip()

                if not clean_course:
                    continue

                if not any(
                    clean_course.lower() == existing.lower()
                    for existing in add_courses
                ):
                    add_courses.append(clean_course)

        # ------------------------------------------------------
        # DISPLAY SELECTED COURSES
        # ------------------------------------------------------

        if add_courses:

            st.info(
                "Assigned courses: "
                + ", ".join(add_courses)
            )

        else:

            st.warning(
                "No course has been selected yet."
            )

        # ------------------------------------------------------
        # CONTACT
        # ------------------------------------------------------

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

        st.markdown(
            "**Zoom Classroom Information**"
        )

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

        st.markdown(
            "**Portal Login Credentials**"
        )

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
        # ADD STUDENT
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

            elif not add_courses:

                st.error(
                    "Please select at least one course."
                )

            else:

                clean_code = code.strip()
                clean_first = first.strip()
                clean_last = last.strip()
                clean_email = email.strip().lower()
                clean_username = username.strip().lower()
                clean_grade = grade.strip()

                clean_subject = courses_to_subject(
                    add_courses
                )

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
                # USERNAME DUPLICATE CHECK
                # ==================================================

                existing_username = query_dataframe(
                    """
                    SELECT id
                    FROM users
                    WHERE LOWER(TRIM(username)) = %s
                    LIMIT 1
                    """,
                    (clean_username,)
                )

                if not existing_username.empty:

                    st.warning(
                        f"The username '{clean_username}' "
                        "is already in use."
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
                    "subject": "Courses",
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
    
        st.subheader("Archive Students")
    
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
            WHERE COALESCE(archived, 0) = 1
            ORDER BY id DESC
            """
        )
    
        if not archived_students.empty:
    
            archived_students["Student Name"] = (
                archived_students["first_name"].fillna("")
                + " "
                + archived_students["last_name"].fillna("")
            ).str.strip()
    
            # ======================================================
            # DISPLAY ARCHIVED STUDENTS
            # ======================================================
    
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
                    "subject": "Courses",
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
    
            # ======================================================
            # SELECT ARCHIVED STUDENT
            # ======================================================
    
            archived_options = archived_students["id"].tolist()
    
            selected_archived_id = st.selectbox(
                "Select Archived Student",
                archived_options,
                format_func=lambda x: (
                    f"{archived_students.loc["
                        archived_students["id"] == x,
                        "Student Name"
                    ].iloc[0]} "
                    f"(ID: {x})"
                ),
                key="archived_student_select"
            )
    
            selected_archived_row = archived_students[
                archived_students["id"] == selected_archived_id
            ].iloc[0]
    
            selected_student_name = (
                selected_archived_row["Student Name"]
            )
    
            # ======================================================
            # RESTORE STUDENT
            # ======================================================
    
            st.subheader("Restore Student")
    
            st.info(
                f"Restore **{selected_student_name}** "
                f"(ID: {selected_archived_id}) to the active student list. "
                "All homework, grades, attendance, sessions, payments, "
                "login information, and other history will remain."
            )
    
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
                        (int(selected_archived_id),)
                    )
    
                    st.cache_data.clear()
    
                    if hasattr(st, "cache_resource"):
                        st.cache_resource.clear()
    
                    st.success(
                        f"{selected_student_name} "
                        "has been restored successfully."
                    )
    
                    st.rerun()
    
                except Exception as e:
    
                    st.error(
                        f"Error restoring student: {e}"
                    )
    
            # ======================================================
            # PERMANENT DELETE
            # ======================================================
    
            st.divider()
    
            st.subheader("🗑️ Permanently Delete Student")
    
            st.warning(
                f"⚠️ This will permanently delete "
                f"**{selected_student_name}** "
                f"(ID: {selected_archived_id}) "
                "and the student's database records."
            )
    
            st.caption(
                "This action cannot be undone. "
                "Use this only when you are certain that the "
                "student and their historical records are no longer needed."
            )
    
            # ------------------------------------------------------
            # CONFIRMATION
            # ------------------------------------------------------
    
            confirm_delete = st.checkbox(
                f"I understand that permanently deleting "
                f"{selected_student_name} cannot be undone.",
                key="confirm_delete_archived_student"
            )
    
            if st.button(
                "🗑️ Permanently Delete Student",
                type="secondary",
                disabled=not confirm_delete,
                key="permanent_delete_student_button"
            ):
    
                try:
    
                    student_id_to_delete = int(
                        selected_archived_id
                    )
    
                    # ==================================================
                    # DELETE RELATED RECORDS FIRST
                    # ==================================================
    
                    # --------------------------------------------------
                    # Homework grades
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM homework_grades
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Attendance
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM attendance
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Payments
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM payments
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Sessions / Schedule
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM sessions
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Progress Notes
                    #
                    # If this table exists in your database, delete
                    # the student's records.
                    # --------------------------------------------------
    
                    try:
    
                        execute(
                            """
                            DELETE FROM progress_notes
                            WHERE student_id = %s
                            """,
                            (student_id_to_delete,)
                        )
    
                    except Exception:
                        # Ignore if progress_notes does not exist
                        pass
    
                    # --------------------------------------------------
                    # Reports
                    # --------------------------------------------------
    
                    try:
    
                        execute(
                            """
                            DELETE FROM reports
                            WHERE student_id = %s
                            """,
                            (student_id_to_delete,)
                        )
    
                    except Exception:
                        # Ignore if reports does not exist
                        pass
    
                    # --------------------------------------------------
                    # Homework
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM homework
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Student login account
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM users
                        WHERE student_id = %s
                        """,
                        (student_id_to_delete,)
                    )
    
                    # --------------------------------------------------
                    # Finally delete the student
                    # --------------------------------------------------
    
                    execute(
                        """
                        DELETE FROM students
                        WHERE id = %s
                        AND COALESCE(archived, 0) = 1
                        """,
                        (student_id_to_delete,)
                    )
    
                    # ==================================================
                    # CLEAR CACHE
                    # ==================================================
    
                    st.cache_data.clear()
    
                    if hasattr(st, "cache_resource"):
                        st.cache_resource.clear()
    
                    st.success(
                        f"{selected_student_name} "
                        "and the student's database records "
                        "have been permanently deleted."
                    )
    
                    st.rerun()
    
                except Exception as e:
    
                    st.error(
                        f"Error permanently deleting student: {e}"
                    )
    
        else:
    
            st.info(
                "There are currently no archived students."
            )

    # ==========================================================
    # TAB 4 — EDIT STUDENT
    # ==========================================================

    with tab4:

        st.subheader(
            "Edit Student Information"
        )

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

            student_id = int(
                student_row["id"]
            )

            # ==================================================
            # EXISTING COURSES
            # ==================================================

            existing_courses = parse_courses(
                student_row["subject"]
            )

            # ==================================================
            # EDIT FORM
            # ==================================================

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

                # --------------------------------------------------
                # COURSES
                # --------------------------------------------------

                st.markdown("---")

                st.markdown(
                    "**Courses**"
                )

                st.caption(
                    "Select all courses assigned to this student."
                )

                edit_courses = []

                edit_course_columns = st.columns(2)

                for index, course in enumerate(
                    COURSE_OPTIONS
                ):

                    with edit_course_columns[
                        index % 2
                    ]:

                        selected = st.checkbox(
                            course,
                            value=any(
                                course.lower() == existing.lower()
                                for existing in existing_courses
                            ),
                            key=(
                                f"edit_course_"
                                f"{student_id}_"
                                f"{course}"
                            )
                        )

                        if selected:

                            edit_courses.append(
                                course
                            )

                # --------------------------------------------------
                # OTHER EXISTING COURSES
                # --------------------------------------------------

                known_courses_lower = {
                    course.lower()
                    for course in COURSE_OPTIONS
                }

                other_existing_courses = [
                    course
                    for course in existing_courses
                    if course.lower()
                    not in known_courses_lower
                ]

                default_other = ", ".join(
                    other_existing_courses
                )

                e_other_course = st.text_input(
                    "Other Course (optional)",
                    value=default_other,
                    key=f"edit_other_course_{student_id}",
                    placeholder="Example: Statistics"
                )

                if e_other_course.strip():

                    other_courses = [
                        course.strip()
                        for course in e_other_course.split(",")
                        if course.strip()
                    ]

                    for course in other_courses:

                        if not any(
                            course.lower() == existing.lower()
                            for existing in edit_courses
                        ):
                            edit_courses.append(course)

                # --------------------------------------------------
                # CURRENT COURSE SUMMARY
                # --------------------------------------------------

                if edit_courses:

                    st.info(
                        "Assigned courses: "
                        + ", ".join(edit_courses)
                    )

                else:

                    st.warning(
                        "No course has been selected."
                    )

                # --------------------------------------------------
                # CONTACT
                # --------------------------------------------------

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

                current_username_result = query_dataframe(
                    """
                    SELECT username
                    FROM users
                    WHERE student_id = %s
                    ORDER BY username
                    LIMIT 1
                    """,
                    (student_id,)
                )

                current_username = ""

                if not current_username_result.empty:

                    current_username = str(
                        current_username_result.iloc[0]["username"]
                    )

                e_username = st.text_input(
                    "Username",
                    value=current_username,
                    key=f"edit_username_{student_id}"
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

                # --------------------------------------------------
                # SUBMIT
                # --------------------------------------------------

                submit_edit = st.form_submit_button(
                    "Update Student Record",
                    type="primary"
                )

                if submit_edit:

                    if (
                        not e_first.strip()
                        or not e_last.strip()
                    ):

                        st.error(
                            "First name and last name are required."
                        )

                    elif not edit_courses:

                        st.error(
                            "Please select at least one course."
                        )

                    elif not e_username.strip():

                        st.error(
                            "Username is required."
                        )

                    else:

                        try:

                            clean_username = (
                                e_username.strip().lower()
                            )

                            # ======================================
                            # USERNAME DUPLICATE CHECK
                            # ======================================

                            duplicate_username = query_dataframe(
                                """
                                SELECT id
                                FROM users
                                WHERE LOWER(TRIM(username)) = %s
                                  AND student_id <> %s
                                LIMIT 1
                                """,
                                (
                                    clean_username,
                                    student_id
                                )
                            )

                            if not duplicate_username.empty:

                                st.error(
                                    f"The username "
                                    f"'{clean_username}' "
                                    "is already being used by "
                                    "another account."
                                )

                                return

                            # ======================================
                            # CLEAN COURSE LIST
                            # ======================================

                            final_courses = []

                            for course in edit_courses:

                                clean_course = (
                                    str(course).strip()
                                )

                                if not clean_course:
                                    continue

                                if any(
                                    clean_course.lower()
                                    == existing.lower()
                                    for existing in final_courses
                                ):
                                    continue

                                final_courses.append(
                                    clean_course
                                )

                            clean_subject = courses_to_subject(
                                final_courses
                            )

                            # ======================================
                            # UPDATE STUDENT
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
                                    clean_subject,
                                    e_email.strip().lower(),
                                    e_phone.strip(),
                                    e_zoom.strip(),
                                    e_meeting.strip(),
                                    e_parent_pin.strip(),
                                    student_id
                                )
                            )

                            # ======================================
                            # UPDATE USERNAME
                            # ======================================

                            execute(
                                """
                                UPDATE users
                                SET username = %s
                                WHERE student_id = %s
                                """,
                                (
                                    clean_username,
                                    student_id
                                )
                            )

                            # ======================================
                            # UPDATE PASSWORD IF PROVIDED
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
