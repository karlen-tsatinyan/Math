import streamlit as st
import os
import io
import uuid
import pandas as pd

from datetime import date

from PIL import Image
from pypdf import PdfReader, PdfWriter

from database import execute, query_dataframe
from supabase_client import get_supabase

from modules.ai_grader import grade_homework_with_ai


# ============================================================
# HELPER: SAFE VALUE
# ============================================================

def safe_text(value):
    """
    Safely convert database values to clean strings.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


# ============================================================
# HELPER: GET STUDENT COURSES
# ============================================================

def get_student_courses(student_id):
    """
    Return the courses assigned to a student.

    Courses are currently stored in:

        students.subject

    Example:

        Algebra, Geometry
    """

    result = query_dataframe(
        """
        SELECT subject
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (student_id,)
    )

    courses = []

    if result.empty:
        return courses

    subject = result.iloc[0]["subject"]

    if subject is None:
        return courses

    subject_text = str(subject).strip()

    if (
        not subject_text
        or subject_text.lower() in ["nan", "none"]
    ):
        return courses

    courses = [
        course.strip()
        for course in subject_text.split(",")
        if course.strip()
    ]

    # Remove duplicates while preserving order
    courses = list(
        dict.fromkeys(courses)
    )

    return courses


# ============================================================
# CREATE SINGLE PDF FROM MULTIPLE FILES
# ============================================================

def merge_homework_files(uploaded_files):
    """
    Combine multiple uploaded images/PDFs
    into one PDF file.

    Returns:
        bytes
    """

    pdf_writer = PdfWriter()

    for uploaded_file in uploaded_files:

        file_bytes = uploaded_file.getvalue()

        filename = uploaded_file.name.lower()

        # --------------------------------------------
        # PDF FILE
        # --------------------------------------------

        if filename.endswith(".pdf"):

            reader = PdfReader(
                io.BytesIO(file_bytes)
            )

            for page in reader.pages:

                pdf_writer.add_page(page)

        # --------------------------------------------
        # IMAGE FILE
        # --------------------------------------------

        elif filename.endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):

            image = Image.open(
                io.BytesIO(file_bytes)
            ).convert("RGB")

            img_buffer = io.BytesIO()

            image.save(
                img_buffer,
                format="PDF"
            )

            img_buffer.seek(0)

            reader = PdfReader(
                img_buffer
            )

            for page in reader.pages:

                pdf_writer.add_page(page)

    output = io.BytesIO()

    pdf_writer.write(
        output
    )

    output.seek(0)

    return output.getvalue()


# ============================================================
# NORMALIZE SUPABASE STORAGE PATH
# ============================================================

def normalize_storage_path(storage_path):
    """
    Convert different possible stored formats into
    the path expected by Supabase Storage.
    """

    if storage_path is None:
        return None

    path = str(storage_path).strip()

    if not path:
        return None

    # --------------------------------------------------------
    # Remove bucket prefix
    # --------------------------------------------------------

    if path.startswith("homework-files/"):

        path = path[
            len("homework-files/"):
        ]

    # --------------------------------------------------------
    # Handle full Supabase Storage URLs
    # --------------------------------------------------------

    if "/storage/v1/object/" in path:

        path = path.split(
            "/storage/v1/object/",
            1
        )[1]

        if path.startswith("public/"):

            path = path[
                len("public/"):
            ]

        elif path.startswith("sign/"):

            path = path[
                len("sign/"):
            ]

        elif path.startswith("authenticated/"):

            path = path[
                len("authenticated/"):
            ]

        if path.startswith(
            "homework-files/"
        ):

            path = path[
                len("homework-files/"):
            ]

    # --------------------------------------------------------
    # Handle full URL containing bucket name
    # --------------------------------------------------------

    if path.startswith("http"):

        if "homework-files/" in path:

            path = path.split(
                "homework-files/",
                1
            )[1]

    return path.strip("/")


# ============================================================
# CREATE SIGNED URL
# ============================================================

def get_homework_file_url(storage_path):
    """
    Create a temporary signed URL for a private
    Supabase Storage object.
    """

    path = normalize_storage_path(
        storage_path
    )

    if not path:
        return None

    try:

        supabase = get_supabase()

        result = (
            supabase
            .storage
            .from_("homework-files")
            .create_signed_url(
                path,
                3600
            )
        )

        data = result

        if hasattr(result, "data"):

            data = result.data

        if isinstance(data, dict):

            signed_url = (
                data.get("signedURL")
                or data.get("signedUrl")
                or data.get("signed_url")
                or data.get("url")
            )

            if signed_url:

                return signed_url

        return None

    except Exception as e:

        st.error(
            f"Unable to create homework file link: {e}"
        )

        return None


# ============================================================
# DOWNLOAD SUPABASE STORAGE FILE
# ============================================================

def download_homework_file(storage_path):
    """
    Download a homework file from the private
    homework-files bucket.

    Returns:
        bytes
        or None
    """

    path = normalize_storage_path(
        storage_path
    )

    if not path:
        return None

    try:

        supabase = get_supabase()

        response = (
            supabase
            .storage
            .from_("homework-files")
            .download(path)
        )

        if response:

            return response

        return None

    except Exception as e:

        st.error(
            f"Unable to download homework file: {e}"
        )

        return None


# ============================================================
# DELETE SUPABASE STORAGE FILE
# ============================================================

def delete_homework_file(storage_path):

    path = normalize_storage_path(
        storage_path
    )

    if not path:
        return True

    try:

        supabase = get_supabase()

        supabase.storage.from_(
            "homework-files"
        ).remove(
            [path]
        )

        return True

    except Exception as e:

        st.error(
            f"Storage delete failed: {e}"
        )

        return False


# ============================================================
# ARCHIVED HOMEWORK
# ============================================================

def archived_homework():

    st.subheader(
        "📦 Archived Homework"
    )

    archived = query_dataframe(
        """
        SELECT
            h.id,
            s.first_name || ' ' || s.last_name
                AS student,
            h.course,
            h.title,
            h.curriculum_topic,
            h.grade,
            h.teacher_feedback,
            h.assigned_date,
            h.due_date,
            h.archived_at

        FROM homework h

        JOIN students s
            ON h.student_id = s.id

        WHERE h.archived = 1

        ORDER BY h.archived_at DESC
        """
    )

    if archived.empty:

        st.info(
            "No archived homework."
        )

        return

    st.dataframe(
        archived,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ========================================================
    # SELECT ARCHIVED HOMEWORK
    # ========================================================

    archive_options = {
        f"#{int(row['id'])} — "
        f"{safe_text(row['student'])} — "
        f"{safe_text(row['course'])} — "
        f"{safe_text(row['title'])}":

        int(row["id"])

        for _, row in archived.iterrows()
    }

    selected_archive = st.selectbox(
        "Select Archived Homework",
        list(archive_options.keys()),
        key="archived_homework_select"
    )

    archive_id = archive_options[
        selected_archive
    ]

    # ========================================================
    # RESTORE / DELETE
    # ========================================================

    col1, col2 = st.columns(2)

    # ========================================================
    # RESTORE
    # ========================================================

    with col1:

        if st.button(
            "↩ Restore Homework",
            key=f"restore_archived_{archive_id}"
        ):

            execute(
                """
                UPDATE homework

                SET
                    archived = 0,
                    status = 'Reviewed',
                    deleted_assignment_file = 0,
                    deleted_student_file = 0

                WHERE id = %s
                """,
                (
                    archive_id,
                )
            )

            st.cache_data.clear()

            st.success(
                "✅ Homework restored successfully."
            )

            st.rerun()

    # ========================================================
    # PERMANENT DELETE
    # ========================================================

    with col2:

        confirm_delete = st.checkbox(
            "I understand this permanently removes this homework record.",
            key=f"confirm_archive_delete_{archive_id}"
        )

        if st.button(
            "🗑 Permanently Delete Record",
            key=f"delete_archived_{archive_id}"
        ):

            if not confirm_delete:

                st.warning(
                    "Please confirm permanent deletion first."
                )

                st.stop()

            execute(
                """
                DELETE FROM homework
                WHERE id = %s
                """,
                (
                    archive_id,
                )
            )

            st.cache_data.clear()

            st.success(
                "🗑 Homework permanently deleted."
            )

            st.rerun()


# ============================================================
# ADMIN HOMEWORK MANAGEMENT
# ============================================================

def homework_management():

    st.header(
        "Teacher Homework Management"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Assign Homework",
            "Review & Grade Submissions",
            "Archived Homework"
        ]
    )

    # ========================================================
    # GET STUDENTS
    # ========================================================

    students = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        WHERE COALESCE(archived, 0) = 0
        ORDER BY last_name, first_name
        """
    )

    if students.empty:

        st.warning(
            "No active students available."
        )

        return

    selected_student_id = (
        st.session_state.get(
            "selected_student"
        )
    )

    student_names = (
        students["name"].tolist()
    )

    default_index = 0

    if selected_student_id is not None:

        match = students[
            students["id"] == selected_student_id
        ]

        if not match.empty:

            matching_positions = [
                i
                for i, value in enumerate(
                    students["id"].tolist()
                )
                if value == selected_student_id
            ]

            if matching_positions:

                default_index = (
                    matching_positions[0]
                )

    # ========================================================
    # TAB 1 — ASSIGN HOMEWORK
    # ========================================================

    with tab1:

        st.subheader(
            "Assign New Homework"
        )

        student_name = st.selectbox(
            "Student",
            student_names,
            index=default_index,
            key="assign_student"
        )

        student_id = int(
            students[
                students["name"] == student_name
            ]["id"].iloc[0]
        )

        st.session_state.selected_student = (
            student_id
        )

        # ====================================================
        # COURSE SELECTION
        # ====================================================

        student_courses = get_student_courses(
            student_id
        )

        if not student_courses:

            st.warning(
                "This student does not have any "
                "courses assigned."
            )

            st.info(
                "Please open Edit Student and add "
                "the student's courses first."
            )

            return

        selected_course = st.selectbox(
            "Course",
            student_courses,
            key=f"assign_homework_course_{student_id}"
        )

        st.caption(
            f"Homework will be assigned to: "
            f"**{student_name} → {selected_course}**"
        )

        # ====================================================
        # HOMEWORK DETAILS
        # ====================================================

        title = st.text_input(
            "Homework Title",
            key="homework_title"
        )

        curriculum = st.text_input(
            "Curriculum Topic",
            key="homework_curriculum"
        )

        assigned_date = st.date_input(
            "Assigned Date",
            value=date.today(),
            key="homework_assigned_date"
        )

        due_date = st.date_input(
            "Due Date",
            key="homework_due_date"
        )

        priority = st.selectbox(
            "Priority",
            [
                "Normal",
                "Important"
            ],
            key="homework_priority"
        )

        uploaded_file = st.file_uploader(
            "Upload Assignment",
            type=[
                "pdf",
                "jpg",
                "jpeg",
                "png"
            ],
            key="teacher_upload"
        )

        drive_link = st.text_input(
            "Google Drive Link",
            key="homework_drive_link"
        )

        comment = st.text_area(
            "Instructions / Comments",
            key="homework_comment"
        )

        st.divider()

        # ====================================================
        # ASSIGN HOMEWORK
        # ====================================================

        if st.button(
            "➕ Assign Homework",
            key="assign_homework_button",
            type="primary"
        ):

            if not title.strip():

                st.error(
                    "Please enter a Homework Title."
                )

                return

            if (
                not uploaded_file
                and not drive_link.strip()
            ):

                st.error(
                    "Please upload an assignment "
                    "PDF/image or provide a Google Drive link."
                )

                return

            # ==================================================
            # PREVENT DUPLICATE
            # ==================================================

            duplicate = query_dataframe(
                """
                SELECT id
                FROM homework
                WHERE student_id = %s
                AND course = %s
                AND title = %s
                AND assigned_date = %s
                AND due_date = %s
                AND archived = 0
                """,
                (
                    student_id,
                    selected_course,
                    title.strip(),
                    str(assigned_date),
                    str(due_date)
                )
            )

            if not duplicate.empty:

                st.warning(
                    "⚠️ This homework already exists "
                    "for this student and course."
                )

                st.stop()

            file_path = None

            # ==================================================
            # SAVE ASSIGNMENT TO SUPABASE STORAGE
            # ==================================================

            if uploaded_file:

                supabase = get_supabase()

                bucket_name = (
                    "homework-files"
                )

                safe_filename = os.path.basename(
                    uploaded_file.name
                )

                storage_path = (
                    f"assignments/"
                    f"student_{student_id}/"
                    f"{date.today()}_"
                    f"{safe_filename}"
                )

                file_bytes = (
                    uploaded_file.getvalue()
                )

                try:

                    supabase.storage.from_(
                        bucket_name
                    ).upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={
                            "content-type": (
                                uploaded_file.type
                                or "application/octet-stream"
                            ),
                            "upsert": "true"
                        }
                    )

                    file_path = (
                        storage_path
                    )

                except Exception as e:

                    st.error(
                        "❌ The assignment could not "
                        "be uploaded to Supabase Storage."
                    )

                    st.exception(e)

                    return

            # ==================================================
            # INSERT HOMEWORK RECORD
            # ==================================================

            execute(
                """
                INSERT INTO homework
                (
                    student_id,
                    course,
                    uploaded_by,
                    title,
                    curriculum_topic,
                    assigned_date,
                    due_date,
                    priority,
                    assignment_file,
                    file_link,
                    comment,
                    status,
                    archived,
                    deleted_assignment_file,
                    deleted_student_file
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    student_id,
                    selected_course,
                    "admin",
                    title.strip(),
                    curriculum.strip(),
                    str(assigned_date),
                    str(due_date),
                    priority,
                    file_path,
                    drive_link.strip() or None,
                    comment.strip(),
                    "Assigned",
                    0,
                    0,
                    0
                )
            )

            st.cache_data.clear()

            st.success(
                f"✅ Homework assigned successfully "
                f"to {student_name} for {selected_course}."
            )

            st.rerun()

    # ========================================================
    # TAB 2 — REVIEW & GRADE
    # ========================================================

    with tab2:

        st.subheader(
            "Review & Grade Submissions"
        )

        submissions = query_dataframe(
            """
            SELECT
                h.id,
                h.student_id,
                h.course,

                s.first_name || ' ' || s.last_name
                    AS student_name,

                h.title,
                h.curriculum_topic,
                h.assigned_date,
                h.due_date,
                h.priority,
                h.assignment_file,
                h.student_file,
                h.file_link,
                h.status,
                h.comment,
                h.teacher_feedback,
                h.grade,
                h.deleted_assignment_file,
                h.deleted_student_file,
                h.submitted_at,
                h.reviewed_at,
                h.created_at

            FROM homework h

            JOIN students s
                ON h.student_id = s.id

            WHERE h.archived = 0

            ORDER BY h.created_at DESC
            """
        )

        if submissions.empty:

            st.info(
                "No homework submissions found."
            )

            return

        # ====================================================
        # SUBMISSION TABLE
        # ====================================================

        display_columns = [
            "id",
            "student_name",
            "course",
            "title",
            "curriculum_topic",
            "status",
            "grade",
            "due_date",
            "submitted_at"
        ]

        st.dataframe(
            submissions[
                display_columns
            ].rename(
                columns={
                    "id": "Homework ID",
                    "student_name": "Student",
                    "course": "Course",
                    "title": "Homework",
                    "curriculum_topic": "Curriculum Topic",
                    "status": "Status",
                    "grade": "Grade",
                    "due_date": "Due Date",
                    "submitted_at": "Submitted"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ====================================================
        # SELECT HOMEWORK
        # ====================================================

        homework_options = {}

        for _, row in submissions.iterrows():

            label = (
                f"#{int(row['id'])} — "
                f"{safe_text(row['student_name'])} — "
                f"{safe_text(row['course'])} — "
                f"{safe_text(row['title'])} — "
                f"{safe_text(row['status'])}"
            )

            homework_options[
                label
            ] = int(row["id"])

        selected_label = st.selectbox(
            "Select Homework to Review",
            list(homework_options.keys()),
            key="review_homework_select"
        )

        selected_id = (
            homework_options[
                selected_label
            ]
        )

        selected_rows = submissions[
            submissions["id"] == selected_id
        ]

        if selected_rows.empty:

            st.error(
                "Unable to find the selected homework."
            )

            return

        selected = (
            selected_rows.iloc[0]
        )

        # ====================================================
        # HOMEWORK INFORMATION
        # ====================================================

        st.subheader(
            f"📚 {safe_text(selected['title'])}"
        )

        info1, info2, info3, info4 = st.columns(4)

        with info1:

            st.write(
                "**Student:**",
                safe_text(
                    selected["student_name"]
                )
            )

        with info2:

            st.write(
                "**Course:**",
                safe_text(
                    selected["course"]
                )
            )

        with info3:

            st.write(
                "**Due Date:**",
                safe_text(
                    selected["due_date"]
                )
            )

        with info4:

            st.write(
                "**Status:**",
                safe_text(
                    selected["status"]
                )
            )

        if safe_text(
            selected["curriculum_topic"]
        ):

            st.write(
                "**Curriculum Topic:**",
                safe_text(
                    selected["curriculum_topic"]
                )
            )

        if safe_text(
            selected["comment"]
        ):

            st.info(
                "Instructions: "
                + safe_text(
                    selected["comment"]
                )
            )

        # ====================================================
        # ORIGINAL ASSIGNMENT
        # ====================================================

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

        assignment_deleted = (
            selected["deleted_assignment_file"]
        )

        deleted_assignment = (
            int(assignment_deleted or 0)
            if pd.notna(assignment_deleted)
            else 0
        )

        if deleted_assignment == 1:

            st.warning(
                "The original assignment file "
                "has been deleted."
            )

        elif safe_text(assignment_file):

            assignment_url = (
                get_homework_file_url(
                    assignment_file
                )
            )

            if assignment_url:

                st.link_button(
                    "📥 Open / Download Assignment",
                    assignment_url
                )

            else:

                st.error(
                    "Unable to create the Supabase "
                    "Storage link for this assignment."
                )

        elif safe_text(assignment_link):

            st.link_button(
                "🔗 Open Google Drive Assignment",
                safe_text(
                    assignment_link
                )
            )

        else:

            st.info(
                "No original assignment file "
                "or link is available."
            )

        # ====================================================
        # STUDENT SUBMISSION
        # ====================================================

        st.divider()

        st.subheader(
            "📝 Student Submission"
        )

        student_file = selected[
            "student_file"
        ]

        student_deleted = selected[
            "deleted_student_file"
        ]

        deleted_student = (
            int(student_deleted or 0)
            if pd.notna(student_deleted)
            else 0
        )

        if deleted_student == 1:

            st.warning(
                "The student's submitted file "
                "has been deleted."
            )

        elif safe_text(student_file):

            student_path = str(
                student_file
            ).strip()

            student_url = (
                get_homework_file_url(
                    student_path
                )
            )

            if student_url:

                st.success(
                    "✅ Student submission is available."
                )

                st.link_button(
                    "📥 Open / Download Student Work",
                    student_url
                )

                st.caption(
                    "Open the student's completed homework "
                    "to review and grade it."
                )

            else:

                st.error(
                    "The student's submission is recorded, "
                    "but the file could not be opened from "
                    "Supabase Storage."
                )

        else:

            st.info(
                "No student submission is available."
            )

        # ==================================================
        # GRADE OPTIONS
        # ==================================================

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

        # ==================================================
        # AI HOMEWORK REVIEW
        # ==================================================

        st.divider()

        st.subheader(
            "🤖 AI Homework Review"
        )

        st.caption(
            "AI provides a grading recommendation only. "
            "The teacher remains responsible for the final grade."
        )

        # ==================================================
        # CHECK STUDENT SUBMISSION
        # ==================================================

        if (
            deleted_student == 0
            and safe_text(student_file)
        ):

            if st.button(
                "✨ Analyze Student Work with AI",
                key=f"ai_grader_review_button_homework_{int(selected_id)}",
                type="primary"
            ):

                with st.spinner(
                    "🤖 Gemini is analyzing the student's homework..."
                ):

                    # ----------------------------------------
                    # DOWNLOAD STUDENT PDF
                    # ----------------------------------------

                    pdf_bytes = download_homework_file(
                        student_file
                    )

                    if not pdf_bytes:

                        st.error(
                            "❌ Unable to download the student's "
                            "homework from Supabase Storage."
                        )

                        st.stop()

                    # ----------------------------------------
                    # HOMEWORK INFORMATION
                    # ----------------------------------------

                    homework_title = safe_text(
                        selected["title"]
                    )

                    curriculum_topic = safe_text(
                        selected["curriculum_topic"]
                    )

                    instructions = safe_text(
                        selected["comment"]
                    )

                    # ----------------------------------------
                    # SEND TO GEMINI
                    # ----------------------------------------

                    result = grade_homework_with_ai(
                        pdf_bytes=pdf_bytes,
                        homework_title=homework_title,
                        curriculum_topic=curriculum_topic,
                        instructions=instructions
                    )

                    # ----------------------------------------
                    # STORE RESULT
                    # ----------------------------------------

                    if result.get("success"):

                        st.session_state[
                            f"ai_result_{selected_id}"
                        ] = result

                        st.success(
                            "✅ Gemini analysis completed."
                        )

                    else:

                        st.error(
                            "❌ Gemini could not analyze "
                            "the homework."
                        )

                        st.error(
                            result.get(
                                "error",
                                "Unknown AI error."
                            )
                        )

            # =================================================
            # DISPLAY AI RESULT
            # =================================================

            ai_result = st.session_state.get(
                f"ai_result_{selected_id}"
            )

            if ai_result:

                st.divider()

                st.subheader(
                    "🤖 Gemini Recommendation"
                )

                # ---------------------------------------------
                # GRADE / SCORE / CONFIDENCE
                # ---------------------------------------------

                ai_grade = safe_text(
                    ai_result.get(
                        "suggested_grade"
                    )
                )

                ai_percentage = ai_result.get(
                    "suggested_percentage",
                    0
                )

                ai_confidence = safe_text(
                    ai_result.get(
                        "confidence"
                    )
                )

                metric1, metric2, metric3 = st.columns(3)

                with metric1:

                    st.metric(
                        "Suggested Grade",
                        ai_grade
                        if ai_grade
                        else "N/A"
                    )

                with metric2:

                    st.metric(
                        "Estimated Score",
                        f"{ai_percentage}%"
                    )

                with metric3:

                    st.metric(
                        "Confidence",
                        ai_confidence
                        if ai_confidence
                        else "Unknown"
                    )

                # ---------------------------------------------
                # SUMMARY
                # ---------------------------------------------

                ai_summary = safe_text(
                    ai_result.get(
                        "summary"
                    )
                )

                if ai_summary:

                    st.markdown(
                        "**Overall Assessment**"
                    )

                    st.info(
                        ai_summary
                    )

                # ---------------------------------------------
                # STRENGTHS
                # ---------------------------------------------

                strengths = ai_result.get(
                    "strengths",
                    []
                )

                if strengths:

                    st.markdown(
                        "### ✅ Strengths"
                    )

                    for strength in strengths:

                        st.write(
                            f"• {strength}"
                        )

                # ---------------------------------------------
                # MISTAKES
                # ---------------------------------------------

                mistakes = ai_result.get(
                    "mistakes",
                    []
                )

                if mistakes:

                    st.markdown(
                        "### ⚠️ Areas to Review"
                    )

                    for mistake in mistakes:

                        st.write(
                            f"• {mistake}"
                        )

                # ---------------------------------------------
                # PROBLEM ANALYSIS
                # ---------------------------------------------

                problem_analysis = ai_result.get(
                    "problem_analysis",
                    []
                )

                if problem_analysis:

                    st.markdown(
                        "### 📊 Problem Analysis"
                    )

                    for problem in problem_analysis:

                        problem_number = safe_text(
                            problem.get(
                                "problem"
                            )
                        )

                        problem_result = safe_text(
                            problem.get(
                                "result"
                            )
                        )

                        explanation = safe_text(
                            problem.get(
                                "explanation"
                            )
                        )

                        with st.expander(
                            f"Problem {problem_number} — "
                            f"{problem_result}"
                        ):

                            st.write(
                                explanation
                            )

                # ---------------------------------------------
                # SUGGESTED FEEDBACK
                # ---------------------------------------------

                ai_feedback = safe_text(
                    ai_result.get(
                        "feedback"
                    )
                )

                if ai_feedback:

                    st.markdown(
                        "### 📝 Suggested Teacher Feedback"
                    )

                    st.info(
                        ai_feedback
                    )

                # ---------------------------------------------
                # AI REASONING
                # ---------------------------------------------

                ai_reasoning = safe_text(
                    ai_result.get(
                        "reasoning"
                    )
                )

                if ai_reasoning:

                    with st.expander(
                        "🔎 Why Gemini Suggested This Grade"
                    ):

                        st.write(
                            ai_reasoning
                        )

                # ---------------------------------------------
                # USE AI GRADE
                # ---------------------------------------------

                st.divider()

                st.caption(
                    "The AI suggestion will NOT automatically "
                    "change the official grade."
                )

                if ai_grade in grade_options:

                    if st.button(
                        f"Use AI Suggested Grade ({ai_grade})",
                        key=f"ai_grader_use_grade_homework_{int(selected_id)}"
                    ):

                        st.session_state[
                            f"grade_select_{int(selected_id)}"
                        ] = ai_grade

                        st.success(
                            f"AI grade {ai_grade} loaded into "
                            "the Grade field below."
                        )

                        st.rerun()

                # ---------------------------------------------
                # USE AI FEEDBACK
                # ---------------------------------------------

                if ai_feedback:

                    if st.button(
                        "Use AI Suggested Feedback",
                        key=f"ai_grader_use_feedback_homework_{int(selected_id)}"
                    ):

                        st.session_state[
                            f"feedback_{int(selected_id)}"
                        ] = ai_feedback

                        st.success(
                            "AI feedback loaded into "
                            "the Teacher Feedback field below."
                        )

                        st.rerun()

        else:

            st.info(
                "AI review is available after the student "
                "has submitted a homework file."
            )

        # ==================================================
        # ARCHIVE HOMEWORK
        # ==================================================

        st.divider()

        if st.button(
            "📦 Archive Homework",
            key=f"archive_homework_{selected_id}"
        ):

            assignment_file = selected[
                "assignment_file"
            ]

            student_file = selected[
                "student_file"
            ]

            # ----------------------------------------------
            # DELETE ASSIGNMENT FILE
            # ----------------------------------------------

            if safe_text(assignment_file):

                delete_homework_file(
                    assignment_file
                )

            # ----------------------------------------------
            # DELETE STUDENT SUBMISSION
            # ----------------------------------------------

            if safe_text(student_file):

                delete_homework_file(
                    student_file
                )

            # ----------------------------------------------
            # ARCHIVE DATABASE RECORD
            # ----------------------------------------------

            execute(
                """
                UPDATE homework

                SET
                    archived = 1,
                    assignment_file = NULL,
                    student_file = NULL,
                    deleted_assignment_file = 1,
                    deleted_student_file = 1,
                    status = 'Archived',
                    archived_at = CURRENT_TIMESTAMP

                WHERE id = %s
                """,
                (
                    int(selected_id),
                )
            )

            st.cache_data.clear()

            st.success(
                "📦 Homework archived. "
                "Academic record preserved."
            )

            st.rerun()

        # ==================================================
        # GRADE SAVE CONFIRMATION
        # ==================================================

        if (
            st.session_state.get(
                "grade_feedback_saved"
            )
            == int(selected_id)
        ):

            st.success(
                "✅ Grade and teacher feedback saved successfully."
            )

            del st.session_state[
                "grade_feedback_saved"
            ]

        st.divider()

        st.subheader(
            "📝 Grade & Teacher Feedback"
        )

        # ==================================================
        # GRADE
        # ==================================================

        current_grade = safe_text(
            selected["grade"]
        )

        if current_grade not in grade_options:

            current_grade = ""

        grade_key = (
            f"grade_select_{int(selected_id)}"
        )

        if grade_key not in st.session_state:

            st.session_state[
                grade_key
            ] = current_grade

        grade = st.selectbox(
            "Letter Grade",
            grade_options,
            key=grade_key
        )

        # ==================================================
        # FEEDBACK
        # ==================================================

        current_feedback = safe_text(
            selected["teacher_feedback"]
        )

        feedback_key = (
            f"feedback_{int(selected_id)}"
        )

        if feedback_key not in st.session_state:

            st.session_state[
                feedback_key
            ] = current_feedback

        feedback = st.text_area(
            "Teacher Feedback",
            key=feedback_key
        )

        # ==================================================
        # SAVE GRADE
        # ==================================================

        if st.button(
            "💾 Save Grade & Feedback",
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

            st.session_state[
                "grade_feedback_saved"
            ] = int(selected_id)

            st.rerun()

    # ========================================================
    # TAB 3 — ARCHIVED HOMEWORK
    # ========================================================

    with tab3:

        archived_homework()


# ============================================================
# STUDENT HOMEWORK PORTAL
# ============================================================

def student_homework():

    # ========================================================
    # STUDENT ID
    # ========================================================

    student_id = st.session_state.user[
        "student_id"
    ]

    # ========================================================
    # SELECTED COURSE
    # ========================================================

    selected_course = (
        st.session_state.user.get(
            "selected_course"
        )
    )

    if not selected_course:

        st.warning(
            "Please select a course before opening homework."
        )

        return

    # ========================================================
    # PAGE HEADER
    # ========================================================

    st.header(
        f"📚 My Homework — {selected_course}"
    )

    st.caption(
        f"Showing homework for **{selected_course}** only."
    )

    # ========================================================
    # GET STUDENT HOMEWORK
    # ========================================================

    homework = query_dataframe(
        """
        SELECT
            id,
            title,
            description,
            course,
            curriculum_topic,
            assigned_date,
            due_date,
            priority,
            assignment_file,
            file_link,
            student_file,
            comment,
            teacher_feedback,
            grade,
            status,
            created_at,
            submitted_at,
            reviewed_at,
            deleted_assignment_file,
            deleted_student_file

        FROM homework

        WHERE student_id = %s
        AND course = %s
        AND archived = 0

        ORDER BY
            CASE
                WHEN status = 'Assigned' THEN 0
                WHEN status = 'Submitted' THEN 1
                WHEN status = 'Reviewed' THEN 2
                ELSE 3
            END,

            due_date ASC NULLS LAST,
            created_at DESC
        """,
        (
            student_id,
            selected_course
        )
    )

    # ========================================================
    # NO HOMEWORK
    # ========================================================

    if homework.empty:

        st.info(
            f"🎉 You currently have no "
            f"{selected_course} homework assignments."
        )

        return

    # ========================================================
    # HOMEWORK SELECTOR
    # ========================================================

    st.subheader(
        "Select Homework"
    )

    homework_options = []

    for _, row in homework.iterrows():

        title = (
            str(row["title"])
            if pd.notna(row["title"])
            and str(row["title"]).strip()
            else f"Homework #{row['id']}"
        )

        status = (
            str(row["status"])
            if pd.notna(row["status"])
            else "Assigned"
        )

        due = (
            str(row["due_date"])
            if pd.notna(row["due_date"])
            else "No due date"
        )

        homework_options.append(
            f"{title} | Due: {due} | {status}"
        )

    selected_option = st.selectbox(
        "Homework Assignment",
        homework_options,
        key=f"student_homework_selector_{selected_course}"
    )

    selected_index = (
        homework_options.index(
            selected_option
        )
    )

    selected = (
        homework.iloc[selected_index]
    )

    selected_id = int(
        selected["id"]
    )

    # ========================================================
    # SUBMISSION SUCCESS
    # ========================================================

    if (
        st.session_state.get(
            "homework_submission_success"
        )
        == selected_id
    ):

        st.success(
            "✅ Homework submitted successfully!"
        )

        del st.session_state[
            "homework_submission_success"
        ]

    # ========================================================
    # SELECTED HOMEWORK
    # ========================================================

    title = (
        str(selected["title"])
        if pd.notna(selected["title"])
        and str(selected["title"]).strip()
        else f"Homework #{selected_id}"
    )

    st.title(
        f"📘 {title}"
    )

    # ========================================================
    # COURSE BADGE
    # ========================================================

    st.info(
        f"📚 Course: **{selected_course}**"
    )

    # ========================================================
    # STATUS / GRADE
    # ========================================================

    status = (
        str(selected["status"])
        if pd.notna(selected["status"])
        else "Assigned"
    )

    grade = selected["grade"]

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Status",
            status
        )

    with c2:

        due_display = (
            str(selected["due_date"])
            if pd.notna(selected["due_date"])
            else "No due date"
        )

        st.metric(
            "Due Date",
            due_display
        )

    with c3:

        if (
            pd.notna(grade)
            and str(grade).strip()
        ):

            st.metric(
                "Grade",
                str(grade)
            )

        else:

            st.metric(
                "Grade",
                "Not graded"
            )

    # ========================================================
    # ASSIGNMENT INFORMATION
    # ========================================================

    st.divider()

    st.subheader(
        "📋 Assignment Information"
    )

    col1, col2 = st.columns(2)

    with col1:

        topic = selected[
            "curriculum_topic"
        ]

        st.write(
            "**📚 Curriculum Topic:**",
            topic
            if pd.notna(topic)
            and str(topic).strip()
            else "Not specified"
        )

        assigned_date = selected[
            "assigned_date"
        ]

        st.write(
            "**📅 Assigned:**",
            assigned_date
            if pd.notna(assigned_date)
            else "Not specified"
        )

    with col2:

        priority = selected[
            "priority"
        ]

        st.write(
            "**⚡ Priority:**",
            priority
            if pd.notna(priority)
            and str(priority).strip()
            else "Normal"
        )

        due_date = selected[
            "due_date"
        ]

        st.write(
            "**⏰ Due:**",
            due_date
            if pd.notna(due_date)
            else "No due date"
        )

    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    instructions = selected[
        "comment"
    ]

    description = selected[
        "description"
    ]

    if (
        pd.notna(instructions)
        and str(instructions).strip()
    ):

        st.subheader(
            "📝 Instructions"
        )

        st.info(
            str(instructions)
        )

    elif (
        pd.notna(description)
        and str(description).strip()
    ):

        st.subheader(
            "📝 Instructions"
        )

        st.info(
            str(description)
        )

    # ========================================================
    # AI LEARNING REFERENCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 📖 Need Help With This Topic?"
    )

    st.caption(
        "Get a short explanation, worked example, "
        "common mistakes, and an interactive visualization "
        "when appropriate."
    )

    if st.button(
        "✨ Learn This Topic",
        key=f"learn_topic_homework_{int(selected_id)}",
        type="primary"
    ):

        with st.spinner(
            "🤖 Creating your topic reference..."
        ):

            from modules.ai_learning_reference import (
                generate_learning_reference
            )

            # ----------------------------------------------
            # HOMEWORK INFORMATION
            # ----------------------------------------------

            homework_title = safe_text(
                selected["title"]
            )

            curriculum_topic = safe_text(
                selected["curriculum_topic"]
            )

            instructions = safe_text(
                selected["comment"]
            )

            # ----------------------------------------------
            # GET STUDENT GRADE LEVEL
            # ----------------------------------------------

            student_info = query_dataframe(
                """
                SELECT
                    grade
                FROM students
                WHERE id = %s
                LIMIT 1
                """,
                (student_id,)
            )

            student_grade = ""

            if not student_info.empty:

                student_grade = safe_text(
                    student_info.iloc[0]["grade"]
                )

            # ----------------------------------------------
            # GENERATE REFERENCE
            # ----------------------------------------------

            result = generate_learning_reference(

                curriculum_topic=curriculum_topic,

                homework_title=homework_title,

                instructions=instructions,

                student_grade=student_grade
            )

        # ----------------------------------------------
        # STORE RESULT
        # ----------------------------------------------

        if result.get("success"):

            st.session_state[
                f"learning_reference_{int(selected_id)}"
            ] = result

            st.success(
                "✅ Topic reference created."
            )

        else:

            st.error(
                result.get(
                    "error",
                    "Unable to create topic reference."
                )
            )

    # ========================================================
    # DISPLAY AI TOPIC REFERENCE
    # ========================================================

    learning_reference = st.session_state.get(
        f"learning_reference_{int(selected_id)}"
    )

    if learning_reference:

        from modules.ai_learning_reference import (
            display_learning_reference
        )

        with st.container(
            border=True
        ):

            display_learning_reference(
                learning_reference
            )

    # ========================================================
    # ORIGINAL ASSIGNMENT
    # ========================================================

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

    assignment_deleted = (
        selected["deleted_assignment_file"]
    )

    deleted_assignment = (
        int(assignment_deleted or 0)
        if pd.notna(assignment_deleted)
        else 0
    )

    if deleted_assignment == 1:

        st.warning(
            "The original assignment file "
            "has been deleted."
        )

    elif safe_text(assignment_file):

        assignment_url = (
            get_homework_file_url(
                assignment_file
            )
        )

        if assignment_url:

            st.link_button(
                "📥 Open / Download Assignment",
                assignment_url
            )

        else:

            st.error(
                "Unable to create a Supabase "
                "Storage link."
            )

    elif safe_text(assignment_link):

        st.link_button(
            "🔗 Open Google Drive Assignment",
            safe_text(
                assignment_link
            )
        )

    else:

        st.info(
            "No original assignment file "
            "or link is available."
        )

    # ========================================================
    # MY SUBMISSION
    # ========================================================

    st.divider()

    st.subheader(
        "📤 My Submission"
    )

    student_file = selected[
        "student_file"
    ]

    student_file_deleted = selected[
        "deleted_student_file"
    ]

    deleted_student = (
        int(student_file_deleted or 0)
        if pd.notna(student_file_deleted)
        else 0
    )

    if deleted_student == 1:

        st.warning(
            "Your submitted homework file "
            "has been deleted."
        )

    elif safe_text(student_file):

        student_path = str(
            student_file
        ).strip()

        student_url = (
            get_homework_file_url(
                student_path
            )
        )

        if student_url:

            st.success(
                "✅ Your completed homework has been submitted."
            )

            st.link_button(
                "📥 View / Download My Submission",
                student_url
            )

        else:

            st.error(
                "Unable to create a Supabase Storage "
                "link for your submission."
            )

    else:

        if status == "Reviewed":

            st.info(
                "Your homework has been reviewed."
            )

        else:

            st.info(
                "You have not submitted this homework yet."
            )

    # ========================================================
    # UPLOAD COMPLETED HOMEWORK
    # ========================================================

    if status != "Reviewed":

        st.divider()

        st.subheader(
            "📤 Submit Completed Homework"
        )

        uploads = st.file_uploader(
            "Select Homework Files",
            type=[
                "pdf",
                "jpg",
                "jpeg",
                "png"
            ],
            accept_multiple_files=True,
            key=f"student_upload_{selected_id}"
        )

        existing_submission = safe_text(
            selected["student_file"]
        )

        if existing_submission:

            st.warning(
                "⚠️ You already submitted this homework. "
                "Uploading again will replace your previous submission."
            )

            confirm_replace = st.checkbox(
                "I want to replace my previous submission.",
                key=f"confirm_replace_{selected_id}"
            )

        else:

            confirm_replace = True

        if st.button(
            "Submit Homework",
            key=f"submit_homework_{selected_id}"
        ):

            if (
                existing_submission
                and not confirm_replace
            ):

                st.error(
                    "Please confirm replacement before uploading."
                )

                st.stop()

            if not uploads:

                st.warning(
                    "Please select at least one file."
                )

            else:

                with st.spinner(
                    "Combining files and uploading PDF..."
                ):

                    # ----------------------------------------
                    # MERGE FILES
                    # ----------------------------------------

                    merged_pdf = merge_homework_files(
                        uploads
                    )

                    # ----------------------------------------
                    # REMOVE OLD SUBMISSION
                    # ----------------------------------------

                    if existing_submission:

                        delete_homework_file(
                            existing_submission
                        )

                    # ----------------------------------------
                    # UPLOAD NEW PDF
                    # ----------------------------------------

                    supabase = get_supabase()

                    bucket_name = (
                        "homework-files"
                    )

                    unique_id = (
                        uuid.uuid4().hex[:10]
                    )

                    storage_path = (
                        f"submissions/"
                        f"student_{student_id}/"
                        f"homework_{selected_id}_"
                        f"{unique_id}.pdf"
                    )

                    try:

                        supabase.storage.from_(
                            bucket_name
                        ).upload(

                            path=storage_path,

                            file=merged_pdf,

                            file_options={
                                "content-type":
                                    "application/pdf"
                            }
                        )

                    except Exception as e:

                        st.error(
                            "❌ Upload failed."
                        )

                        st.exception(e)

                        return

                    # ----------------------------------------
                    # UPDATE HOMEWORK
                    # ----------------------------------------

                    execute(
                        """
                        UPDATE homework

                        SET
                            student_file = %s,
                            status = 'Submitted',
                            submitted_at = CURRENT_TIMESTAMP,
                            deleted_student_file = 0

                        WHERE id = %s
                        AND student_id = %s
                        AND course = %s
                        """,
                        (
                            storage_path,
                            selected_id,
                            student_id,
                            selected_course
                        )
                    )

                    st.cache_data.clear()

                    st.session_state[
                        "homework_submission_success"
                    ] = int(selected_id)

                    st.success(
                        "✅ Homework uploaded successfully."
                    )

                    st.rerun()

    # ========================================================
    # TEACHER FEEDBACK
    # ========================================================

    if (
        pd.notna(
            selected["teacher_feedback"]
        )
        and str(
            selected["teacher_feedback"]
        ).strip()
    ):

        st.divider()

        st.subheader(
            "👩‍🏫 Teacher Feedback"
        )

        st.success(
            str(
                selected["teacher_feedback"]
            )
        )

    # ========================================================
    # GRADE
    # ========================================================

    if (
        pd.notna(grade)
        and str(grade).strip()
    ):

        st.divider()

        st.subheader(
            "🏆 Your Grade"
        )

        st.success(
            f"Grade: **{grade}**"
        )
