import os
from datetime import date
import pandas as pd
import streamlit as st

from database import execute, query_dataframe
from config import UPLOAD_FOLDER


# ==========================================
# HOMEWORK DATABASE SCHEMA CHECK
# ==========================================

def ensure_homework_schema():
    """
    Ensure the homework table contains the columns
    used by the current Supabase/PostgreSQL version.

    IMPORTANT:
    This uses assignment_file and student_file.
    There is NO file_path column.
    """

    try:

        execute(
            """
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL
                    REFERENCES students(id)
                    ON DELETE CASCADE,

                uploaded_by TEXT DEFAULT 'admin',

                title TEXT,
                curriculum_topic TEXT,

                assigned_date DATE DEFAULT CURRENT_DATE,
                due_date DATE DEFAULT CURRENT_DATE,

                priority TEXT DEFAULT 'Normal',

                assignment_file TEXT,
                student_file TEXT,
                file_link TEXT,

                comment TEXT,
                teacher_feedback TEXT,

                grade TEXT,

                status TEXT DEFAULT 'Assigned',

                deleted_assignment_file INTEGER DEFAULT 0,
                deleted_student_file INTEGER DEFAULT 0,

                submitted_at TIMESTAMP,
                reviewed_at TIMESTAMP,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        columns_to_add = [

            ("uploaded_by", "TEXT DEFAULT 'admin'"),
            ("title", "TEXT"),
            ("curriculum_topic", "TEXT"),
            ("assigned_date", "DATE DEFAULT CURRENT_DATE"),
            ("due_date", "DATE DEFAULT CURRENT_DATE"),
            ("priority", "TEXT DEFAULT 'Normal'"),

            ("assignment_file", "TEXT"),
            ("student_file", "TEXT"),
            ("file_link", "TEXT"),

            ("comment", "TEXT"),
            ("teacher_feedback", "TEXT"),

            ("grade", "TEXT"),

            ("status", "TEXT DEFAULT 'Assigned'"),

            ("deleted_assignment_file", "INTEGER DEFAULT 0"),
            ("deleted_student_file", "INTEGER DEFAULT 0"),

            ("submitted_at", "TIMESTAMP"),
            ("reviewed_at", "TIMESTAMP"),

            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]

        for col_name, col_type in columns_to_add:

            try:

                execute(
                    f"""
                    ALTER TABLE homework
                    ADD COLUMN IF NOT EXISTS
                    {col_name} {col_type}
                    """
                )

            except Exception:
                pass

    except Exception:
        pass


# ==========================================
# ADMIN / TEACHER HOMEWORK MANAGEMENT
# ==========================================

def homework_management():

    st.header("📚 Teacher Homework Management")

    ensure_homework_schema()

    students = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        ORDER BY last_name, first_name
        """
    )

    if students.empty:

        st.warning(
            "No students available. Please add students first."
        )

        return

    # --------------------------------------
    # STUDENT OPTIONS
    # --------------------------------------

    student_options = {
        f"{row['name']} (ID: {row['id']})": int(row["id"])
        for _, row in students.iterrows()
    }

    saved_student_id = st.session_state.get(
        "selected_student_id"
    )

    default_index = 0

    if saved_student_id is not None:

        for idx, student_id in enumerate(
            student_options.values()
        ):

            if int(student_id) == int(saved_student_id):

                default_index = idx
                break

    tab1, tab2 = st.tabs(
        [
            "Assign Homework",
            "Review Submissions"
        ]
    )


    # ======================================
    # TAB 1 — ASSIGN HOMEWORK
    # ======================================

    with tab1:

        st.subheader(
            "Assign New Homework"
        )

        selected_label = st.selectbox(
            "Select Student",
            options=list(student_options.keys()),
            index=default_index,
            key="assign_student_select"
        )

        student_id = student_options[
            selected_label
        ]

        st.session_state.selected_student_id = (
            student_id
        )


        with st.form(
            "assign_homework_form",
            clear_on_submit=True
        ):

            title = st.text_input(
                "Homework Title",
                placeholder="e.g., Quadratic Equations Worksheet"
            )

            curriculum = st.text_input(
                "Curriculum Topic",
                placeholder="e.g., Algebra II - Ch. 4"
            )


            col_dates = st.columns(2)

            with col_dates[0]:

                assigned_date = st.date_input(
                    "Assigned Date",
                    value=date.today()
                )

            with col_dates[1]:

                due_date = st.date_input(
                    "Due Date",
                    value=date.today()
                )


            priority = st.selectbox(
                "Priority",
                [
                    "Normal",
                    "Important"
                ]
            )


            uploaded_file = st.file_uploader(
                "Upload Assignment PDF/Image",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png"
                ],
                key="teacher_upload_file"
            )


            drive_link = st.text_input(
                "Google Drive / External Link (Optional)"
            )


            comment = st.text_area(
                "Instructions for Student"
            )


            submitted = st.form_submit_button(
                "📤 Assign Homework"
            )


            if submitted:

                if not title.strip():

                    st.error(
                        "Please enter a homework title."
                    )

                elif due_date < assigned_date:

                    st.error(
                        "Due Date cannot be earlier than Assigned Date."
                    )

                else:

                    assignment_file = None

                    os.makedirs(
                        UPLOAD_FOLDER,
                        exist_ok=True
                    )


                    # --------------------------------
                    # SAVE TEACHER ASSIGNMENT FILE
                    # --------------------------------

                    if uploaded_file:

                        safe_name = os.path.basename(
                            uploaded_file.name
                        )

                        filename = (
                            f"{student_id}_"
                            f"{assigned_date}_"
                            f"{safe_name}"
                        )

                        assignment_file = os.path.join(
                            UPLOAD_FOLDER,
                            filename
                        )


                        with open(
                            assignment_file,
                            "wb"
                        ) as f:

                            f.write(
                                uploaded_file.getbuffer()
                            )


                    # --------------------------------
                    # CLEAN GOOGLE DRIVE LINK
                    # --------------------------------

                    clean_link = drive_link.strip()

                    if clean_link and not clean_link.startswith(
                        ("http://", "https://")
                    ):

                        clean_link = (
                            "https://" + clean_link
                        )


                    # --------------------------------
                    # INSERT HOMEWORK
                    # --------------------------------

                    execute(
                        """
                        INSERT INTO homework
                        (
                            student_id,
                            uploaded_by,
                            title,
                            curriculum_topic,
                            assigned_date,
                            due_date,
                            priority,
                            assignment_file,
                            file_link,
                            comment,
                            status
                        )
                        VALUES
                        (
                            %s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s
                        )
                        """,
                        (
                            student_id,
                            "admin",
                            title.strip(),
                            curriculum.strip(),
                            assigned_date.isoformat(),
                            due_date.isoformat(),
                            priority,
                            assignment_file,
                            clean_link if clean_link else None,
                            comment.strip(),
                            "Assigned"
                        )
                    )


                    st.cache_data.clear()

                    st.success(
                        "Homework assigned successfully!"
                    )

                    st.rerun()


    # ======================================
    # TAB 2 — REVIEW SUBMISSIONS
    # ======================================

    with tab2:

        st.subheader(
            "Review & Grade Submissions"
        )


        # ----------------------------------
        # ONLY SUBMITTED WORK
        # ----------------------------------

        submissions = query_dataframe(
            """
            SELECT

                h.id,

                h.student_id,

                COALESCE(
                    h.title,
                    'Untitled'
                ) AS title,

                COALESCE(
                    h.curriculum_topic,
                    ''
                ) AS curriculum_topic,

                s.first_name || ' ' ||
                s.last_name AS student_name,

                h.assigned_date,
                h.due_date,

                h.assignment_file,

                h.student_file,

                h.file_link,

                COALESCE(
                    h.status,
                    'Assigned'
                ) AS status,

                COALESCE(
                    h.teacher_feedback,
                    ''
                ) AS teacher_feedback,

                COALESCE(
                    h.grade,
                    ''
                ) AS grade,

                h.submitted_at,
                h.reviewed_at,
                h.created_at

            FROM homework h

            JOIN students s
                ON h.student_id = s.id

            WHERE h.status IN (
                'Submitted',
                'Reviewed'
            )

            ORDER BY
                h.submitted_at DESC NULLS LAST,
                h.created_at DESC
            """
        )


        if submissions.empty:

            st.info(
                "No student homework submissions found."
            )

        else:

            st.success(
                f"{len(submissions)} submission(s) available for review."
            )


            # ----------------------------------
            # SELECT SUBMISSION
            # ----------------------------------

            submission_map = {}

            for _, row in submissions.iterrows():

                label = (
                    f"#{row['id']} — "
                    f"{row['student_name']} — "
                    f"{row['title']} "
                    f"({row['status']})"
                )

                submission_map[label] = int(
                    row["id"]
                )


            selected_label = st.selectbox(
                "Select Homework Submission",
                options=list(
                    submission_map.keys()
                ),
                key="review_homework_select"
            )


            selected_id = submission_map[
                selected_label
            ]


            selected = submissions[
                submissions["id"] == selected_id
            ].iloc[0]


            st.divider()


            # ==================================
            # STUDENT / ASSIGNMENT INFORMATION
            # ==================================

            st.subheader(
                f"📚 {selected['title']}"
            )


            col1, col2, col3 = st.columns(3)


            with col1:

                st.write(
                    "**Student:**",
                    selected["student_name"]
                )


            with col2:

                st.write(
                    "**Topic:**",
                    selected["curriculum_topic"]
                    or "Not specified"
                )


            with col3:

                st.write(
                    "**Due Date:**",
                    selected["due_date"]
                    or "Not specified"
                )


            if selected["submitted_at"]:

                st.caption(
                    f"Submitted: {selected['submitted_at']}"
                )


            # ==================================
            # ORIGINAL ASSIGNMENT
            # ==================================

            st.divider()

            st.subheader(
                "📄 Original Assignment"
            )


            assignment_file = (
                selected["assignment_file"]
            )

            assignment_link = (
                selected["file_link"]
            )


            if (
                pd.notna(assignment_file)
                and str(assignment_file).strip()
            ):

                assignment_file = str(
                    assignment_file
                ).strip()


                if os.path.exists(
                    assignment_file
                ):

                    with open(
                        assignment_file,
                        "rb"
                    ) as f:

                        assignment_data = f.read()


                    st.download_button(
                        "📥 Open / Download Assignment",
                        data=assignment_data,
                        file_name=os.path.basename(
                            assignment_file
                        ),
                        key=f"assignment_download_{selected_id}"
                    )

                else:

                    st.warning(
                        "The original assignment file "
                        "is no longer available on the server."
                    )


            elif (
                pd.notna(assignment_link)
                and str(assignment_link).strip()
            ):

                st.link_button(
                    "🔗 Open Google Drive Assignment",
                    str(assignment_link).strip()
                )

            else:

                st.info(
                    "No original assignment file or link is available."
                )


            # ==================================
            # STUDENT SUBMISSION
            # ==================================

            st.divider()

            st.subheader(
                "📝 Student's Submitted Work"
            )


            student_file = (
                selected["student_file"]
            )


            if (
                pd.notna(student_file)
                and str(student_file).strip()
            ):

                student_file = str(
                    student_file
                ).strip()


                if os.path.exists(
                    student_file
                ):

                    st.success(
                        "Student submission is available."
                    )


                    # -----------------------------
                    # OPEN / DOWNLOAD SUBMISSION
                    # -----------------------------

                    with open(
                        student_file,
                        "rb"
                    ) as f:

                        submission_data = f.read()


                    st.download_button(
                        "📥 Open / Download Student Submission",
                        data=submission_data,
                        file_name=os.path.basename(
                            student_file
                        ),
                        key=f"student_submission_download_{selected_id}"
                    )


                    # -----------------------------
                    # IMAGE PREVIEW
                    # -----------------------------

                    extension = os.path.splitext(
                        student_file
                    )[1].lower()


                    if extension in [
                        ".jpg",
                        ".jpeg",
                        ".png"
                    ]:

                        st.image(
                            submission_data,
                            caption="Student Submission",
                            use_container_width=True
                        )


                    # -----------------------------
                    # PDF PREVIEW
                    # -----------------------------

                    elif extension == ".pdf":

                        st.caption(
                            "PDF submission is ready to open/download using the button above."
                        )


                else:

                    st.error(
                        "The student's submitted file "
                        "was recorded in the database, "
                        "but the physical file is no longer "
                        "available on the Streamlit server."
                    )


            else:

                st.warning(
                    "No student submission file was found."
                )


            # ==================================
            # GRADE
            # ==================================

            st.divider()

            st.subheader(
                "🎓 Grade & Feedback"
            )


            grade_options = [
                "",
                "A+",
                "A",
                "A-",
                "B+",
                "B",
                "B-",
                "C+",
                "C",
                "C-",
                "D",
                "F"
            ]


            current_grade = selected["grade"]


            if (
                pd.isna(current_grade)
                or not str(current_grade).strip()
            ):

                current_grade = ""

            else:

                current_grade = str(
                    current_grade
                ).strip()


            if current_grade not in grade_options:

                current_grade = ""


            grade = st.selectbox(
                "Letter Grade",
                options=grade_options,
                index=grade_options.index(
                    current_grade
                ),
                key=f"grade_select_{selected_id}"
            )


            current_feedback = (
                selected["teacher_feedback"]
            )


            if pd.isna(current_feedback):

                current_feedback = ""

            else:

                current_feedback = str(
                    current_feedback
                )


            feedback = st.text_area(
                "Teacher Feedback",
                value=current_feedback,
                key=f"feedback_{selected_id}"
            )


            if st.button(
                "💾 Save Grade & Feedback",
                type="primary",
                key=f"save_grade_{selected_id}"
            ):

                execute(
                    """
                    UPDATE homework

                    SET
                        teacher_feedback = %s,
                        grade = %s,
                        status = 'Reviewed',
                        reviewed_at = CURRENT_TIMESTAMP

                    WHERE id = %s
                    """,
                    (
                        feedback.strip(),
                        grade,
                        int(selected_id)
                    )
                )


                st.cache_data.clear()

                st.success(
                    "Grade and feedback saved successfully."
                )

                st.rerun()


            # ==================================
            # FILE MANAGEMENT
            # ==================================

            st.divider()

            st.subheader(
                "🗑️ File Management"
            )


            col_f1, col_f2 = st.columns(2)


            # ----------------------------------
            # DELETE ASSIGNMENT PDF
            # ----------------------------------

            with col_f1:

                assignment_file = (
                    selected["assignment_file"]
                )


                if (
                    pd.notna(assignment_file)
                    and str(assignment_file).strip()
                    and os.path.exists(
                        str(assignment_file)
                    )
                ):

                    st.success(
                        "Original assignment file is stored."
                    )


                    if st.button(
                        "🗑️ Delete Assignment File",
                        key=f"delete_assignment_{selected_id}"
                    ):

                        try:

                            os.remove(
                                str(assignment_file)
                            )

                        except FileNotFoundError:

                            pass


                        execute(
                            """
                            UPDATE homework

                            SET
                                assignment_file = NULL,
                                deleted_assignment_file = 1

                            WHERE id = %s
                            """,
                            (
                                int(selected_id),
                            )
                        )


                        st.cache_data.clear()

                        st.success(
                            "Assignment file deleted."
                        )

                        st.rerun()

                else:

                    st.caption(
                        "No original assignment file stored."
                    )


            # ----------------------------------
            # DELETE STUDENT SUBMISSION
            # ----------------------------------

            with col_f2:

                student_file = (
                    selected["student_file"]
                )


                if (
                    pd.notna(student_file)
                    and str(student_file).strip()
                    and os.path.exists(
                        str(student_file)
                    )
                ):

                    st.success(
                        "Student submission is stored."
                    )


                    if st.button(
                        "🗑️ Delete Student Submission",
                        key=f"delete_student_{selected_id}"
                    ):

                        try:

                            os.remove(
                                str(student_file)
                            )

                        except FileNotFoundError:

                            pass


                        execute(
                            """
                            UPDATE homework

                            SET
                                student_file = NULL,
                                deleted_student_file = 1

                            WHERE id = %s
                            """,
                            (
                                int(selected_id),
                            )
                        )


                        st.cache_data.clear()

                        st.success(
                            "Student submission file deleted."
                        )

                        st.rerun()

                else:

                    st.caption(
                        "No student submission file stored."
                    )


# ==========================================
# STUDENT HOMEWORK PORTAL
# ==========================================

def student_homework():

    user = st.session_state.get(
        "user",
        {}
    )

    student_id = user.get(
        "student_id"
    )


    if student_id:

        student_id = int(
            student_id
        )


    if not student_id:

        st.error(
            "Student profile missing from session. "
            "Please log in again."
        )

        return


    st.header(
        "📖 My Homework"
    )


    ensure_homework_schema()


    homework = query_dataframe(
        """
        SELECT

            h.id,

            COALESCE(
                h.title,
                ''
            ) AS title,

            COALESCE(
                h.curriculum_topic,
                ''
            ) AS curriculum_topic,

            h.assigned_date,
            h.due_date,

            COALESCE(
                h.priority,
                'Normal'
            ) AS priority,

            h.assignment_file,
            h.student_file,
            h.file_link,

            h.comment,
            h.teacher_feedback,
            h.grade,

            COALESCE(
                h.status,
                'Assigned'
            ) AS status,

            h.created_at

        FROM homework h

        WHERE h.student_id = %s

        ORDER BY h.created_at DESC
        """,
        (
            student_id,
        )
    )


    if homework.empty:

        st.info(
            "No homework assigned yet."
        )

        return


    # ======================================
    # DISPLAY HOMEWORK
    # ======================================

    for _, row in homework.iterrows():

        with st.container(
            border=True
        ):

            st.subheader(
                row["title"]
                or f"Homework #{row['id']}"
            )


            col1, col2 = st.columns(2)


            with col1:

                st.write(
                    "📚 **Topic:**",
                    row["curriculum_topic"]
                    or "N/A"
                )

                st.write(
                    "📅 **Assigned:**",
                    row["assigned_date"]
                )

                st.write(
                    "⏰ **Due:**",
                    row["due_date"]
                )


            with col2:

                st.write(
                    "Priority:",
                    row["priority"]
                )


                if row["status"] == "Assigned":

                    st.warning(
                        "🟡 Waiting for submission"
                    )


                elif row["status"] == "Submitted":

                    st.info(
                        "🔵 Submitted — Awaiting grading"
                    )


                elif row["status"] == "Reviewed":

                    st.success(
                        "🟢 Graded"
                    )


                if (
                    pd.notna(row["grade"])
                    and str(row["grade"]).strip()
                ):

                    st.success(
                        f"**Grade:** {row['grade']}"
                    )


            if (
                pd.notna(row["comment"])
                and str(row["comment"]).strip()
            ):

                st.write(
                    "**Instructions:**"
                )

                st.info(
                    row["comment"]
                )


            # ----------------------------------
            # ASSIGNMENT FILE
            # ----------------------------------

            assignment_file = (
                row["assignment_file"]
            )


            if (
                pd.notna(assignment_file)
                and str(assignment_file).strip()
            ):

                assignment_file = str(
                    assignment_file
                ).strip()


                if os.path.exists(
                    assignment_file
                ):

                    with open(
                        assignment_file,
                        "rb"
                    ) as f:

                        assignment_data = f.read()


                    st.download_button(
                        "📥 Download Assignment File",
                        data=assignment_data,
                        file_name=os.path.basename(
                            assignment_file
                        ),
                        key=f"student_assignment_{row['id']}"
                    )

                else:

                    st.warning(
                        "⚠️ Original assignment file "
                        "is no longer available."
                    )


            # ----------------------------------
            # GOOGLE DRIVE LINK
            # ----------------------------------

            if (
                pd.notna(row["file_link"])
                and str(row["file_link"]).strip()
            ):

                st.link_button(
                    "🔗 Open Assignment Link",
                    str(row["file_link"]).strip()
                )


            # ----------------------------------
            # TEACHER FEEDBACK
            # ----------------------------------

            if (
                pd.notna(row["teacher_feedback"])
                and str(row["teacher_feedback"]).strip()
            ):

                st.write(
                    "**Teacher Feedback:**"
                )

                st.success(
                    row["teacher_feedback"]
                )


    # ======================================
    # SUBMIT COMPLETED HOMEWORK
    # ======================================

    st.divider()

    st.subheader(
        "📤 Submit Completed Homework"
    )


    active_assignments = homework[
        homework["status"] != "Reviewed"
    ]


    if active_assignments.empty:

        st.info(
            "No pending homework to submit."
        )

        return


    assignment_options = {

        (
            f"#{row['id']} - "
            f"{row['title'] or 'Untitled'} "
            f"(Due: {row['due_date']})"
        ): row["id"]

        for _, row in active_assignments.iterrows()
    }


    selected_label = st.selectbox(
        "Select Homework Assignment",
        list(assignment_options.keys()),
        key="student_assignment_select"
    )


    selected_assignment_id = assignment_options[
        selected_label
    ]


    upload = st.file_uploader(
        "Upload Your Completed Homework",
        type=[
            "pdf",
            "jpg",
            "jpeg",
            "png"
        ],
        key="student_solution_upload"
    )


    if st.button(
        "📤 Submit Homework",
        type="primary",
        key="submit_student_homework"
    ):

        if not upload:

            st.error(
                "Please select a file before submitting."
            )

        else:

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )


            safe_name = os.path.basename(
                upload.name
            )


            filename = (
                f"student_"
                f"{student_id}_"
                f"{selected_assignment_id}_"
                f"{safe_name}"
            )


            student_file = os.path.join(
                UPLOAD_FOLDER,
                filename
            )


            with open(
                student_file,
                "wb"
            ) as f:

                f.write(
                    upload.getbuffer()
                )


            # ----------------------------------
            # SAVE STUDENT SUBMISSION
            # ----------------------------------

            execute(
                """
                UPDATE homework

                SET
                    student_file = %s,
                    status = 'Submitted',
                    submitted_at = CURRENT_TIMESTAMP

                WHERE id = %s
                  AND student_id = %s
                """,
                (
                    student_file,
                    int(selected_assignment_id),
                    student_id
                )
            )


            st.cache_data.clear()


            st.success(
                "Homework submitted successfully!"
            )


            st.rerun()
