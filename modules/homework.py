import streamlit as st
import os
import io
import uuid
import pandas as pd

from datetime import date

from PIL import Image

from pypdf import PdfReader, PdfWriter

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from database import execute, query_dataframe
from supabase_client import get_supabase


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
            ).convert(
                "RGB"
            )


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
# HELPER: NORMALIZE SUPABASE STORAGE PATH
# ============================================================

def normalize_storage_path(storage_path):
    """
    Convert different possible stored formats into the
    path expected by Supabase Storage.

    Expected final format:

        assignments/student_1/file.pdf

    or

        submissions/student_1/file.pdf
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
        path = path[len("homework-files/"):]

    # --------------------------------------------------------
    # Handle full Supabase Storage URLs
    # --------------------------------------------------------

    if "/storage/v1/object/" in path:

        path = path.split(
            "/storage/v1/object/",
            1
        )[1]

        if path.startswith("public/"):
            path = path[len("public/"):]

        elif path.startswith("sign/"):
            path = path[len("sign/"):]

        elif path.startswith("authenticated/"):
            path = path[len("authenticated/"):]

        if path.startswith("homework-files/"):
            path = path[len("homework-files/"):]

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
# HELPER: CREATE SIGNED URL
# ============================================================

def get_homework_file_url(storage_path):
    """
    Create a temporary signed URL for a private Supabase
    Storage object.

    Bucket:
        homework-files

    Signed URL lifetime:
        1 hour
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

        # Supabase Python client may return a dictionary
        # or an object containing .data.

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
# HELPER: DELETE SUPABASE STORAGE FILE
# ============================================================

def delete_homework_file(storage_path):
    """
    Delete a homework file from Supabase Storage.

    Returns:
        True  = successful
        False = failed
    """

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
            f"Unable to delete file from Supabase Storage: {e}"
        )

        return False


# ============================================================
# ADMIN HOMEWORK MANAGEMENT
# ============================================================

def homework_management():

    st.header(
        "Teacher Homework Management"
    )

    tab1, tab2 = st.tabs(
        [
            "Assign Homework",
            "Review & Grade Submissions"
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

            # Find actual position in the list
            matching_positions = [
                i
                for i, value in enumerate(
                    students["id"].tolist()
                )
                if value == selected_student_id
            ]

            if matching_positions:
                default_index = matching_positions[0]

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

        if st.button(
            "➕ Assign Homework",
            key="assign_homework_button"
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
                    %s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    student_id,
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
                "✅ Homework assigned successfully."
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
            "title",
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
                    "title": "Homework",
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

        info1, info2, info3 = st.columns(3)

        with info1:

            st.write(
                "**Student:**",
                safe_text(
                    selected["student_name"]
                )
            )

        with info2:

            st.write(
                "**Due Date:**",
                safe_text(
                    selected["due_date"]
                )
            )

        with info3:

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
        # DELETE ORIGINAL ASSIGNMENT
        # ====================================================

        if (
            safe_text(assignment_file)
            and deleted_assignment == 0
        ):

            if st.button(
                "🗑 Delete Assignment File",
                key=f"delete_assignment_{selected_id}"
            ):

                if delete_homework_file(
                    assignment_file
                ):

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
                        "Assignment file deleted "
                        "from Supabase Storage."
                    )

                    st.rerun()

        # ====================================================
        # STUDENT SUBMISSION
        # ====================================================

        st.divider()

        st.subheader(
            "📝 Student Submission"
        )

        student_file = selected["student_file"]

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

        # ====================================================
        # DELETE STUDENT SUBMISSION
        # ====================================================

        if (
            safe_text(student_file)
            and deleted_student == 0
        ):

            if st.button(
                "🗑 Delete Student Submission",
                key=f"delete_student_file_{selected_id}"
            ):

                if delete_homework_file(
                    student_file
                ):

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
                        "Student submission deleted "
                        "from Supabase Storage."
                    )

                    st.rerun()

        # ====================================================
        # GRADE & FEEDBACK SAVE CONFIRMATION
        # ====================================================
        
        if st.session_state.get("grade_feedback_saved") == int(selected_id):
        
            st.success(
                "✅ Grade and teacher feedback saved successfully."
            )
        
            del st.session_state["grade_feedback_saved"]

        st.divider()

        st.subheader(
            "📝 Grade & Teacher Feedback"
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

        current_grade = safe_text(
            selected["grade"]
        )

        if current_grade not in grade_options:

            current_grade = ""

        grade = st.selectbox(
            "Letter Grade",
            grade_options,
            index=grade_options.index(
                current_grade
            ),
            key=f"grade_select_{selected_id}"
        )

        current_feedback = safe_text(
            selected["teacher_feedback"]
        )

        feedback = st.text_area(
            "Teacher Feedback",
            value=current_feedback,
            key=f"feedback_{selected_id}"
        )

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
        
            # Clear cached database results
            st.cache_data.clear()
        
            # Remember which homework was successfully saved
            st.session_state["grade_feedback_saved"] = int(selected_id)
        
            # Reload the page so the updated grade/status appears
            st.rerun()


# ============================================================
# STUDENT HOMEWORK PORTAL
# ============================================================

def student_homework():

    student_id = st.session_state.user["student_id"]

    st.header(
        "📚 My Homework"
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
        )
    )

    # ========================================================
    # NO HOMEWORK
    # ========================================================

    if homework.empty:

        st.info(
            "🎉 You currently have no homework assignments."
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
        key="student_homework_selector"
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
    # SUBMISSION SUCCESS MESSAGE
    # ========================================================

    if (
        st.session_state.get(
            "homework_submission_success"
        ) == selected_id
    ):

        st.success(
            "✅ Homework submitted successfully!"
        )

        del st.session_state[
            "homework_submission_success"
        ]

    # ========================================================
    # SELECTED HOMEWORK DETAILS
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

            st.caption(
                "The assignment is stored securely "
                "in Supabase Storage."
            )

        else:

            st.error(
                "Unable to create the Supabase "
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

        if st.button(
            "Submit Homework",
            key=f"submit_homework_{selected_id}"
        ):

            if not uploads:
            
                st.warning(
                    "Please select at least one file."
                )
            
            
            else:
            
                with st.spinner(
                    "Combining files and uploading PDF..."
                ):
            
                    merged_pdf = merge_homework_files(
                        uploads
                    )
            
            
                    supabase = get_supabase()
            
            
                    bucket_name = "homework-files"
            
            
                    unique_id = uuid.uuid4().hex[:10]

                    storage_path = (
                        f"submissions/"
                        f"student_{student_id}/"
                        f"homework_{selected_id}_"
                        f"{unique_id}"
                        f"{file_extension}"
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
                        """,
            
                        (
                            storage_path,
                            selected_id,
                            student_id
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
