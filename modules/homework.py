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
# HELPERS
# ============================================================

def safe_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def parse_courses(subject):
    """Return a clean list from the student's comma-separated subject field."""
    text = safe_text(subject)
    if not text or text.lower() in {"nan", "none"}:
        return []
    return list(dict.fromkeys([x.strip() for x in text.split(",") if x.strip()]))


def ensure_homework_schema():
    """Add the course column used to keep multi-course homework separate."""
    try:
        execute(
            """
            ALTER TABLE homework
            ADD COLUMN IF NOT EXISTS course TEXT
            """
        )
    except Exception:
        # Keeps the app from crashing on databases where the column already exists
        # or where schema changes are managed externally.
        pass


def clear_caches():
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        if hasattr(st, "cache_resource"):
            st.cache_resource.clear()
    except Exception:
        pass


def merge_homework_files(uploaded_files):
    pdf_writer = PdfWriter()

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name.lower()

        if filename.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                pdf_writer.add_page(page)

        elif filename.endswith((".jpg", ".jpeg", ".png")):
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PDF")
            img_buffer.seek(0)
            reader = PdfReader(img_buffer)
            for page in reader.pages:
                pdf_writer.add_page(page)

    output = io.BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    return output.getvalue()


def normalize_storage_path(storage_path):
    if storage_path is None:
        return None

    path = str(storage_path).strip()
    if not path:
        return None

    if path.startswith("homework-files/"):
        path = path[len("homework-files/"):]

    if "/storage/v1/object/" in path:
        path = path.split("/storage/v1/object/", 1)[1]

        for prefix in ("public/", "sign/", "authenticated/"):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break

        if path.startswith("homework-files/"):
            path = path[len("homework-files/"):]

    if path.startswith("http") and "homework-files/" in path:
        path = path.split("homework-files/", 1)[1]

    return path.strip("/")


def get_homework_file_url(storage_path):
    path = normalize_storage_path(storage_path)
    if not path:
        return None

    try:
        supabase = get_supabase()
        result = (
            supabase.storage.from_("homework-files")
            .create_signed_url(path, 3600)
        )

        data = result.data if hasattr(result, "data") else result
        if isinstance(data, dict):
            return (
                data.get("signedURL")
                or data.get("signedUrl")
                or data.get("signed_url")
                or data.get("url")
            )
        return None
    except Exception as e:
        st.error(f"Unable to create homework file link: {e}")
        return None


def download_homework_file(storage_path):
    path = normalize_storage_path(storage_path)
    if not path:
        return None

    try:
        supabase = get_supabase()
        response = supabase.storage.from_("homework-files").download(path)
        return response if response else None
    except Exception as e:
        st.error(f"Unable to download homework file: {e}")
        return None


def delete_homework_file(storage_path):
    path = normalize_storage_path(storage_path)
    if not path:
        return True

    try:
        supabase = get_supabase()
        supabase.storage.from_("homework-files").remove([path])
        return True
    except Exception as e:
        st.error(f"Storage delete failed: {e}")
        return False


def get_student_courses(student_id):
    result = query_dataframe(
        """
        SELECT subject
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (int(student_id),),
    )
    if result.empty:
        return []
    return parse_courses(result.iloc[0]["subject"])


# ============================================================
# ARCHIVED HOMEWORK
# ============================================================

def archived_homework():
    st.subheader("📦 Archived Homework")

    archived = query_dataframe(
        """
        SELECT
            h.id,
            s.first_name || ' ' || s.last_name AS student,
            h.course,
            h.title,
            h.curriculum_topic,
            h.grade,
            h.teacher_feedback,
            h.assigned_date,
            h.due_date,
            h.archived_at
        FROM homework h
        JOIN students s ON h.student_id = s.id
        WHERE h.archived = 1
        ORDER BY h.archived_at DESC
        """
    )

    if archived.empty:
        st.info("No archived homework.")
        return

    display = archived.rename(columns={"course": "Course"})
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.divider()

    archive_options = {
        f"#{int(row['id'])} — {safe_text(row['student'])} — "
        f"{safe_text(row['course']) or 'Course not specified'} — "
        f"{safe_text(row['title'])}": int(row["id"])
        for _, row in archived.iterrows()
    }

    selected_archive = st.selectbox(
        "Select Archived Homework",
        list(archive_options.keys()),
        key="archived_homework_select",
    )
    archive_id = archive_options[selected_archive]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("↩ Restore Homework", key=f"restore_archived_{archive_id}"):
            execute(
                """
                UPDATE homework
                SET archived = 0,
                    status = 'Reviewed',
                    deleted_assignment_file = 0,
                    deleted_student_file = 0
                WHERE id = %s
                """,
                (archive_id,),
            )
            clear_caches()
            st.success("✅ Homework restored successfully.")
            st.rerun()

    with col2:
        confirm_delete = st.checkbox(
            "I understand this permanently removes this homework record.",
            key=f"confirm_archive_delete_{archive_id}",
        )
        if st.button(
            "🗑 Permanently Delete Record",
            key=f"delete_archived_{archive_id}",
        ):
            if not confirm_delete:
                st.warning("Please confirm permanent deletion first.")
                st.stop()
            execute("DELETE FROM homework WHERE id = %s", (archive_id,))
            clear_caches()
            st.success("🗑 Homework permanently deleted.")
            st.rerun()


# ============================================================
# ADMIN / TEACHER HOMEWORK MANAGEMENT
# ============================================================

def homework_management():
    ensure_homework_schema()

    st.header("Teacher Homework Management")

    tab1, tab2, tab3 = st.tabs(
        ["Assign Homework", "Review & Grade Submissions", "Archived Homework"]
    )

    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------
    students = query_dataframe(
        """
        SELECT
            id,
            first_name,
            last_name,
            subject
        FROM students
        WHERE COALESCE(archived, 0) = 0
        ORDER BY last_name, first_name
        """
    )

    if students.empty:
        st.warning("No active students available.")
        return

    students["name"] = (
        students["first_name"].fillna("")
        + " "
        + students["last_name"].fillna("")
    ).str.strip()

    student_options = {
        f"{row['name']} (ID: {int(row['id'])})": int(row["id"])
        for _, row in students.iterrows()
    }

    # ========================================================
    # TAB 1 — ASSIGN HOMEWORK
    # ========================================================
    with tab1:
        st.subheader("Assign New Homework")

        saved_student_id = st.session_state.get("selected_student")
        labels = list(student_options.keys())
        default_index = 0
        if saved_student_id is not None:
            for i, label in enumerate(labels):
                if student_options[label] == int(saved_student_id):
                    default_index = i
                    break

        selected_student_label = st.selectbox(
            "Student",
            labels,
            index=default_index,
            key="assign_student",
        )
        student_id = student_options[selected_student_label]
        st.session_state.selected_student = student_id

        student_row = students[students["id"] == student_id].iloc[0]
        student_courses = parse_courses(student_row["subject"])

        # IMPORTANT: this is the course assignment that separates Algebra and Geometry.
        if student_courses:
            selected_course = st.selectbox(
                "📚 Course / Class",
                student_courses,
                key=f"assign_course_{student_id}",
                help=(
                    "Choose the student's course. This homework will appear "
                    "only in that course's student portal page."
                ),
            )
        else:
            selected_course = ""
            st.warning(
                "This student does not currently have a course assigned. "
                "Edit the student's Subject/Course field first."
            )

        title = st.text_input("Homework Title", key="homework_title")
        curriculum = st.text_input("Curriculum Topic", key="homework_curriculum")

        assigned_date = st.date_input(
            "Assigned Date", value=date.today(), key="homework_assigned_date"
        )
        due_date = st.date_input("Due Date", key="homework_due_date")

        priority = st.selectbox(
            "Priority", ["Normal", "Important"], key="homework_priority"
        )

        uploaded_file = st.file_uploader(
            "Upload Assignment",
            type=["pdf", "jpg", "jpeg", "png"],
            key="teacher_upload",
        )

        drive_link = st.text_input("Google Drive Link", key="homework_drive_link")
        comment = st.text_area("Instructions / Comments", key="homework_comment")

        st.divider()

        if st.button(
            "➕ Assign Homework",
            key="assign_homework_button",
            type="primary",
        ):
            if not student_courses:
                st.error("Please assign a course to this student before assigning homework.")
                st.stop()

            if not selected_course.strip():
                st.error("Please select the course for this homework.")
                st.stop()

            if not title.strip():
                st.error("Please enter a Homework Title.")
                st.stop()

            if not uploaded_file and not drive_link.strip():
                st.error(
                    "Please upload an assignment PDF/image or provide a Google Drive link."
                )
                st.stop()

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
                LIMIT 1
                """,
                (
                    student_id,
                    selected_course.strip(),
                    title.strip(),
                    str(assigned_date),
                    str(due_date),
                ),
            )

            if not duplicate.empty:
                st.warning(
                    f"⚠️ This homework already exists for {selected_course}."
                )
                st.stop()

            file_path = None

            if uploaded_file:
                supabase = get_supabase()
                safe_filename = os.path.basename(uploaded_file.name)
                storage_path = (
                    f"assignments/student_{student_id}/"
                    f"{date.today()}_{safe_filename}"
                )

                try:
                    supabase.storage.from_("homework-files").upload(
                        path=storage_path,
                        file=uploaded_file.getvalue(),
                        file_options={
                            "content-type": uploaded_file.type
                            or "application/octet-stream",
                            "upsert": "true",
                        },
                    )
                    file_path = storage_path
                except Exception as e:
                    st.error("❌ The assignment could not be uploaded to Supabase Storage.")
                    st.exception(e)
                    st.stop()

            try:
                execute(
                    """
                    INSERT INTO homework
                    (
                        student_id,
                        uploaded_by,
                        course,
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
                        "admin",
                        selected_course.strip(),
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
                        0,
                    ),
                )
            except Exception as e:
                if file_path:
                    delete_homework_file(file_path)
                st.error(f"Error saving homework record: {e}")
                st.stop()

            clear_caches()
            st.success(
                f"✅ Homework assigned successfully to {student_row['name']} — {selected_course}."
            )
            st.rerun()

    # ========================================================
    # TAB 2 — REVIEW & GRADE
    # ========================================================
    with tab2:
        st.subheader("Review & Grade Submissions")

        submissions = query_dataframe(
            """
            SELECT
                h.id,
                h.student_id,
                s.first_name || ' ' || s.last_name AS student_name,
                h.course,
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
            JOIN students s ON h.student_id = s.id
            WHERE h.archived = 0
            ORDER BY h.created_at DESC
            """
        )

        if submissions.empty:
            st.info("No homework submissions found.")
            return

        display_columns = [
            "id", "student_name", "course", "title", "curriculum_topic",
            "status", "grade", "due_date", "submitted_at"
        ]

        st.dataframe(
            submissions[display_columns].rename(
                columns={
                    "id": "Homework ID",
                    "student_name": "Student",
                    "course": "Course",
                    "title": "Homework",
                    "curriculum_topic": "Curriculum Topic",
                    "status": "Status",
                    "grade": "Grade",
                    "due_date": "Due Date",
                    "submitted_at": "Submitted",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        homework_options = {}
        for _, row in submissions.iterrows():
            label = (
                f"#{int(row['id'])} — {safe_text(row['student_name'])} — "
                f"{safe_text(row['course']) or 'Course not specified'} — "
                f"{safe_text(row['title'])} — {safe_text(row['status'])}"
            )
            homework_options[label] = int(row["id"])

        selected_label = st.selectbox(
            "Select Homework to Review",
            list(homework_options.keys()),
            key="review_homework_select",
        )
        selected_id = homework_options[selected_label]

        selected_rows = submissions[submissions["id"] == selected_id]
        if selected_rows.empty:
            st.error("Unable to find the selected homework.")
            return

        selected = selected_rows.iloc[0]

        st.subheader(f"📚 {safe_text(selected['title'])}")

        info1, info2, info3 = st.columns(3)
        with info1:
            st.write("**Student:**", safe_text(selected["student_name"]))
        with info2:
            st.write(
                "**Course:**",
                safe_text(selected["course"]) or "Course not specified",
            )
        with info3:
            st.write("**Status:**", safe_text(selected["status"]))

        if safe_text(selected["curriculum_topic"]):
            st.write("**Curriculum Topic:**", safe_text(selected["curriculum_topic"]))

        if safe_text(selected["comment"]):
            st.info("Instructions: " + safe_text(selected["comment"]))

        # ----------------------------------------------------
        # ORIGINAL ASSIGNMENT
        # ----------------------------------------------------
        st.divider()
        st.subheader("📄 Original Assignment")

        assignment_file = selected["assignment_file"]
        assignment_link = selected["file_link"]
        deleted_assignment = (
            int(selected["deleted_assignment_file"] or 0)
            if pd.notna(selected["deleted_assignment_file"])
            else 0
        )

        if deleted_assignment == 1:
            st.warning("The original assignment file has been deleted.")
        elif safe_text(assignment_file):
            assignment_url = get_homework_file_url(assignment_file)
            if assignment_url:
                st.link_button("📥 Open / Download Assignment", assignment_url)
            else:
                st.error("Unable to create the Supabase Storage link for this assignment.")
        elif safe_text(assignment_link):
            st.link_button("🔗 Open Google Drive Assignment", safe_text(assignment_link))
        else:
            st.info("No original assignment file or link is available.")

        # ----------------------------------------------------
        # STUDENT SUBMISSION
        # ----------------------------------------------------
        st.divider()
        st.subheader("📝 Student Submission")

        student_file = selected["student_file"]
        deleted_student = (
            int(selected["deleted_student_file"] or 0)
            if pd.notna(selected["deleted_student_file"])
            else 0
        )

        if deleted_student == 1:
            st.warning("The student's submitted file has been deleted.")
        elif safe_text(student_file):
            student_url = get_homework_file_url(student_file)
            if student_url:
                st.success("✅ Student submission is available.")
                st.link_button("📥 Open / Download Student Work", student_url)
                st.caption("Open the student's completed homework to review and grade it.")
            else:
                st.error("The student's submission is recorded, but the file could not be opened.")
        else:
            st.info("No student submission is available.")

        # ----------------------------------------------------
        # AI HOMEWORK REVIEW
        # ----------------------------------------------------
        st.divider()
        st.subheader("🤖 AI Homework Review")
        st.caption(
            "AI provides a grading recommendation only. The teacher remains responsible for the final grade."
        )

        if deleted_student == 0 and safe_text(student_file):
            if st.button(
                "✨ Analyze Student Work with AI",
                key=f"ai_grader_review_button_homework_{int(selected_id)}",
                type="primary",
            ):
                with st.spinner("🤖 Gemini is analyzing the student's homework..."):
                    pdf_bytes = download_homework_file(student_file)
                    if not pdf_bytes:
                        st.error("❌ Unable to download the student's homework from Supabase Storage.")
                        st.stop()

                    result = grade_homework_with_ai(
                        pdf_bytes=pdf_bytes,
                        homework_title=safe_text(selected["title"]),
                        curriculum_topic=safe_text(selected["curriculum_topic"]),
                        instructions=safe_text(selected["comment"]),
                    )

                    if result.get("success"):
                        st.session_state[f"ai_result_{selected_id}"] = result
                        st.success("✅ Gemini analysis completed.")
                    else:
                        st.error("❌ Gemini could not analyze the homework.")
                        st.error(result.get("error", "Unknown AI error."))

            ai_result = st.session_state.get(f"ai_result_{selected_id}")
            if ai_result:
                st.divider()
                st.subheader("🤖 Gemini Recommendation")

                ai_grade = safe_text(ai_result.get("suggested_grade"))
                ai_percentage = ai_result.get("suggested_percentage", 0)
                ai_confidence = safe_text(ai_result.get("confidence"))

                metric1, metric2, metric3 = st.columns(3)
                with metric1:
                    st.metric("Suggested Grade", ai_grade or "N/A")
                with metric2:
                    st.metric("Estimated Score", f"{ai_percentage}%")
                with metric3:
                    st.metric("Confidence", ai_confidence or "Unknown")

                ai_summary = safe_text(ai_result.get("summary"))
                if ai_summary:
                    st.markdown("**Overall Assessment**")
                    st.info(ai_summary)

                strengths = ai_result.get("strengths", [])
                if strengths:
                    st.markdown("### ✅ Strengths")
                    for strength in strengths:
                        st.write(f"• {strength}")

                mistakes = ai_result.get("mistakes", [])
                if mistakes:
                    st.markdown("### ⚠️ Areas to Review")
                    for mistake in mistakes:
                        st.write(f"• {mistake}")

                problem_analysis = ai_result.get("problem_analysis", [])
                if problem_analysis:
                    st.markdown("### 📊 Problem Analysis")
                    for problem in problem_analysis:
                        number = safe_text(problem.get("problem"))
                        result_text = safe_text(problem.get("result"))
                        explanation = safe_text(problem.get("explanation"))
                        with st.expander(f"Problem {number} — {result_text}"):
                            st.write(explanation)

                ai_feedback = safe_text(ai_result.get("feedback"))
                if ai_feedback:
                    st.markdown("### 📝 Suggested Teacher Feedback")
                    st.info(ai_feedback)

                ai_reasoning = safe_text(ai_result.get("reasoning"))
                if ai_reasoning:
                    with st.expander("🔎 Why Gemini Suggested This Grade"):
                        st.write(ai_reasoning)

                st.divider()
                st.caption("The AI suggestion will NOT automatically change the official grade.")

                valid_grades = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
                if ai_grade in valid_grades:
                    if st.button(
                        f"Use AI Suggested Grade ({ai_grade})",
                        key=f"ai_grader_use_grade_homework_{int(selected_id)}",
                    ):
                        st.session_state[f"grade_select_{int(selected_id)}"] = ai_grade
                        st.success(f"AI grade {ai_grade} loaded into the Grade field below.")
                        st.rerun()

                if ai_feedback:
                    if st.button(
                        "Use AI Suggested Feedback",
                        key=f"ai_grader_use_feedback_homework_{int(selected_id)}",
                    ):
                        st.session_state[f"feedback_{int(selected_id)}"] = ai_feedback
                        st.success("AI feedback loaded into the Teacher Feedback field below.")
                        st.rerun()
        else:
            st.info("AI review is available after the student has submitted a homework file.")

        # ----------------------------------------------------
        # ARCHIVE
        # ----------------------------------------------------
        st.divider()
        if st.button("📦 Archive Homework", key=f"archive_homework_{selected_id}"):
            if safe_text(selected["assignment_file"]):
                delete_homework_file(selected["assignment_file"])
            if safe_text(selected["student_file"]):
                delete_homework_file(selected["student_file"])

            execute(
                """
                UPDATE homework
                SET archived = 1,
                    assignment_file = NULL,
                    student_file = NULL,
                    deleted_assignment_file = 1,
                    deleted_student_file = 1,
                    status = 'Archived',
                    archived_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (int(selected_id),),
            )
            clear_caches()
            st.success("📦 Homework archived. Academic record preserved.")
            st.rerun()

        # ----------------------------------------------------
        # GRADE & FEEDBACK
        # ----------------------------------------------------
        if st.session_state.get("grade_feedback_saved") == int(selected_id):
            st.success("✅ Grade and teacher feedback saved successfully.")
            del st.session_state["grade_feedback_saved"]

        st.divider()
        st.subheader("📝 Grade & Teacher Feedback")

        grade_options = ["", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]

        current_grade = safe_text(selected["grade"])
        if current_grade not in grade_options:
            current_grade = ""

        grade_key = f"grade_select_{int(selected_id)}"
        if grade_key not in st.session_state:
            st.session_state[grade_key] = current_grade

        grade = st.selectbox("Letter Grade", grade_options, key=grade_key)

        current_feedback = safe_text(selected["teacher_feedback"])
        feedback_key = f"feedback_{int(selected_id)}"
        if feedback_key not in st.session_state:
            st.session_state[feedback_key] = current_feedback

        feedback = st.text_area("Teacher Feedback", key=feedback_key)

        if st.button("💾 Save Grade & Feedback", key=f"save_grade_{selected_id}"):
            execute(
                """
                UPDATE homework
                SET teacher_feedback = %s,
                    grade = %s,
                    status = 'Reviewed',
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (feedback.strip(), grade, int(selected_id)),
            )
            clear_caches()
            st.session_state["grade_feedback_saved"] = int(selected_id)
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
    ensure_homework_schema()

    user = st.session_state.get("user", {})
    student_id = user.get("student_id")

    if student_id is None:
        st.error("Unable to determine the logged-in student.")
        return

    student_id = int(student_id)
    st.header("📚 My Homework")

    # --------------------------------------------------------
    # COURSE SELECTION
    # --------------------------------------------------------
    courses = user.get("courses") or get_student_courses(student_id)
    courses = list(dict.fromkeys([safe_text(c) for c in courses if safe_text(c)]))

    selected_course = safe_text(user.get("selected_course"))

    if len(courses) > 1:
        # Use the login-selected course when valid; otherwise let the student choose.
        current_index = courses.index(selected_course) if selected_course in courses else 0
        selected_course = st.selectbox(
            "📚 Course",
            courses,
            index=current_index,
            key="student_homework_course",
        )
        st.session_state.user["selected_course"] = selected_course
    elif len(courses) == 1:
        selected_course = courses[0]
        st.session_state.user["selected_course"] = selected_course

    # --------------------------------------------------------
    # IMPORTANT: FILTER HOMEWORK BY BOTH STUDENT AND COURSE
    # --------------------------------------------------------
    if selected_course:
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
            (student_id, selected_course),
        )
    else:
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
            (student_id,),
        )

    if homework.empty:
        if selected_course:
            st.info(f"🎉 You currently have no homework for {selected_course}.")
        else:
            st.info("🎉 You currently have no homework assignments.")
        return

    st.subheader("Select Homework")

    homework_options = []
    for _, row in homework.iterrows():
        title = safe_text(row["title"]) or f"Homework #{row['id']}"
        status = safe_text(row["status"]) or "Assigned"
        due = safe_text(row["due_date"]) or "No due date"
        course = safe_text(row["course"])
        course_text = f" | {course}" if course else ""
        homework_options.append(f"{title}{course_text} | Due: {due} | {status}")

    selected_option = st.selectbox(
        "Homework Assignment",
        homework_options,
        key="student_homework_selector",
    )
    selected = homework.iloc[homework_options.index(selected_option)]
    selected_id = int(selected["id"])

    if st.session_state.get("homework_submission_success") == selected_id:
        st.success("✅ Homework submitted successfully!")
        del st.session_state["homework_submission_success"]

    title = safe_text(selected["title"]) or f"Homework #{selected_id}"
    st.title(f"📘 {title}")

    if safe_text(selected["course"]):
        st.caption(f"📚 Course: **{safe_text(selected['course'])}**")

    status = safe_text(selected["status"]) or "Assigned"
    grade = selected["grade"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Status", status)
    with c2:
        due_display = safe_text(selected["due_date"]) or "No due date"
        st.metric("Due Date", due_display)
    with c3:
        st.metric(
            "Grade",
            safe_text(grade) if safe_text(grade) else "Not graded",
        )

    # --------------------------------------------------------
    # ASSIGNMENT INFORMATION
    # --------------------------------------------------------
    st.divider()
    st.subheader("📋 Assignment Information")

    col1, col2 = st.columns(2)
    with col1:
        topic = safe_text(selected["curriculum_topic"])
        st.write("**📚 Curriculum Topic:**", topic or "Not specified")
        st.write("**📅 Assigned:**", safe_text(selected["assigned_date"]) or "Not specified")
    with col2:
        st.write("**⚡ Priority:**", safe_text(selected["priority"]) or "Normal")
        st.write("**⏰ Due:**", safe_text(selected["due_date"]) or "No due date")

    instructions = safe_text(selected["comment"])
    description = safe_text(selected["description"])
    if instructions:
        st.subheader("📝 Instructions")
        st.info(instructions)
    elif description:
        st.subheader("📝 Instructions")
        st.info(description)

    # --------------------------------------------------------
    # AI LEARNING REFERENCE
    # --------------------------------------------------------
    st.divider()
    st.markdown("### 📖 Need Help With This Topic?")
    st.caption(
        "Get a short explanation, worked example, common mistakes, and an interactive visualization when appropriate."
    )

    if st.button(
        "✨ Learn This Topic",
        key=f"learn_topic_homework_{selected_id}",
        type="primary",
    ):
        with st.spinner("🤖 Creating your topic reference..."):
            from modules.ai_learning_reference import generate_learning_reference

            student_info = query_dataframe(
                "SELECT grade FROM students WHERE id = %s LIMIT 1",
                (student_id,),
            )
            student_grade = safe_text(student_info.iloc[0]["grade"]) if not student_info.empty else ""

            result = generate_learning_reference(
                curriculum_topic=safe_text(selected["curriculum_topic"]),
                homework_title=title,
                instructions=instructions,
                student_grade=student_grade,
            )

        if result.get("success"):
            st.session_state[f"learning_reference_{selected_id}"] = result
            st.success("✅ Topic reference created.")
        else:
            st.error(result.get("error", "Unable to create topic reference."))

    learning_reference = st.session_state.get(f"learning_reference_{selected_id}")
    if learning_reference:
        from modules.ai_learning_reference import display_learning_reference
        with st.container(border=True):
            display_learning_reference(learning_reference)

    # --------------------------------------------------------
    # ORIGINAL ASSIGNMENT
    # --------------------------------------------------------
    st.divider()
    st.subheader("📄 Original Assignment")

    assignment_file = selected["assignment_file"]
    assignment_link = selected["file_link"]
    deleted_assignment = (
        int(selected["deleted_assignment_file"] or 0)
        if pd.notna(selected["deleted_assignment_file"])
        else 0
    )

    if deleted_assignment == 1:
        st.warning("The original assignment file has been deleted.")
    elif safe_text(assignment_file):
        assignment_url = get_homework_file_url(assignment_file)
        if assignment_url:
            st.link_button("📥 Open / Download Assignment", assignment_url)
        else:
            st.error("Unable to create a Supabase Storage link.")
    elif safe_text(assignment_link):
        st.link_button("🔗 Open Google Drive Assignment", safe_text(assignment_link))
    else:
        st.info("No original assignment file or link is available.")

    # --------------------------------------------------------
    # MY SUBMISSION
    # --------------------------------------------------------
    st.divider()
    st.subheader("📤 My Submission")

    student_file = selected["student_file"]
    deleted_student = (
        int(selected["deleted_student_file"] or 0)
        if pd.notna(selected["deleted_student_file"])
        else 0
    )

    if deleted_student == 1:
        st.warning("Your submitted homework file has been deleted.")
    elif safe_text(student_file):
        student_url = get_homework_file_url(student_file)
        if student_url:
            st.success("✅ Your completed homework has been submitted.")
            st.link_button("📥 View / Download My Submission", student_url)
        else:
            st.error("Unable to create a Supabase Storage link for your submission.")
    else:
        if status == "Reviewed":
            st.info("Your homework has been reviewed.")
        else:
            st.info("You have not submitted this homework yet.")

    # --------------------------------------------------------
    # UPLOAD COMPLETED HOMEWORK
    # --------------------------------------------------------
    if status != "Reviewed":
        st.divider()
        st.subheader("📤 Submit Completed Homework")

        uploads = st.file_uploader(
            "Select Homework Files",
            type=["pdf", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"student_upload_{selected_id}",
        )

        existing_submission = safe_text(selected["student_file"])

        if existing_submission:
            st.warning(
                "⚠️ You already submitted this homework. Uploading again will replace your previous submission."
            )
            confirm_replace = st.checkbox(
                "I want to replace my previous submission.",
                key=f"confirm_replace_{selected_id}",
            )
        else:
            confirm_replace = True

        if st.button("Submit Homework", key=f"submit_homework_{selected_id}"):
            if existing_submission and not confirm_replace:
                st.error("Please confirm replacement before uploading.")
                st.stop()

            if not uploads:
                st.warning("Please select at least one file.")
                st.stop()

            with st.spinner("Combining files and uploading PDF..."):
                merged_pdf = merge_homework_files(uploads)

                if existing_submission:
                    delete_homework_file(existing_submission)

                supabase = get_supabase()
                unique_id = uuid.uuid4().hex[:10]
                storage_path = (
                    f"submissions/student_{student_id}/"
                    f"homework_{selected_id}_{unique_id}.pdf"
                )

                try:
                    supabase.storage.from_("homework-files").upload(
                        path=storage_path,
                        file=merged_pdf,
                        file_options={"content-type": "application/pdf"},
                    )
                except Exception as e:
                    st.error("❌ Upload failed.")
                    st.exception(e)
                    st.stop()

                execute(
                    """
                    UPDATE homework
                    SET student_file = %s,
                        status = 'Submitted',
                        submitted_at = CURRENT_TIMESTAMP,
                        deleted_student_file = 0
                    WHERE id = %s
                      AND student_id = %s
                    """,
                    (storage_path, selected_id, student_id),
                )

                clear_caches()
                st.session_state["homework_submission_success"] = selected_id
                st.success("✅ Homework uploaded successfully.")
                st.rerun()

    # --------------------------------------------------------
    # TEACHER FEEDBACK
    # --------------------------------------------------------
    if safe_text(selected["teacher_feedback"]):
        st.divider()
        st.subheader("👩‍🏫 Teacher Feedback")
        st.success(safe_text(selected["teacher_feedback"]))

    # --------------------------------------------------------
    # GRADE
    # --------------------------------------------------------
    if safe_text(grade):
        st.divider()
        st.subheader("🏆 Your Grade")
        st.success(f"Grade: **{safe_text(grade)}**")
