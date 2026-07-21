import os
from datetime import date
import pandas as pd
import streamlit as st

from database import execute, query_dataframe
from config import UPLOAD_FOLDER


def ensure_homework_schema():
    """Ensure the homework table exists and contains all required PostgreSQL columns."""
    try:
        # Create table if it doesn't exist
        execute(
            """
            CREATE TABLE IF NOT EXISTS homework (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
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

        # Ensure missing columns are dynamically added if the table pre-existed
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
                execute(f"ALTER TABLE homework ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
            except Exception:
                pass

    except Exception:
        pass


# ==========================================
# ADMIN / TEACHER HOMEWORK MANAGEMENT
# ==========================================

def homework_management():
    st.header("📚 Teacher Homework Management")

    # Run auto-migration check for missing columns
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
        st.warning("No students available. Please add students first.")
        return

    # Build safe student option dictionary mapping
    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"]
        for _, row in students.iterrows()
    }

    # Session state index tracking
    saved_student_id = st.session_state.get("selected_student_id")
    default_index = 0

    if saved_student_id:
        for idx, (label, s_id) in enumerate(student_options.items()):
            if s_id == saved_student_id:
                default_index = idx
                break

    tab1, tab2 = st.tabs(["Assign Homework", "Review Submissions"])

    # --------------------------------------
    # TAB 1: ASSIGN HOMEWORK
    # --------------------------------------
    with tab1:
        st.subheader("Assign New Homework")

        selected_label = st.selectbox(
            "Select Student",
            options=list(student_options.keys()),
            index=default_index,
            key="assign_student_select"
        )

        student_id = student_options[selected_label]
        st.session_state.selected_student_id = student_id

        with st.form("assign_homework_form", clear_on_submit=True):
            title = st.text_input("Homework Title", placeholder="e.g., Quadratic Equations Worksheet")
            curriculum = st.text_input("Curriculum Topic", placeholder="e.g., Algebra II - Ch. 4")

            col_dates = st.columns(2)
            with col_dates[0]:
                assigned_date = st.date_input("Assigned Date", value=date.today())
            with col_dates[1]:
                due_date = st.date_input("Due Date", value=date.today())

            priority = st.selectbox("Priority", ["Normal", "Important"])

            uploaded_file = st.file_uploader(
                "Upload Assignment PDF/Image",
                type=["pdf", "jpg", "jpeg", "png"],
                key="teacher_upload_file"
            )

            drive_link = st.text_input("Google Drive / External Link (Optional)")
            comment = st.text_area("Instructions for Student")

            submitted = st.form_submit_button("📤 Assign Homework")

            if submitted:
                if not title.strip():
                    st.error("Please enter a homework title.")
                else:
                    assignment_file = None
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                    if uploaded_file:
                        filename = f"{student_id}_{date.today()}_{uploaded_file.name}"
                        assignment_file = os.path.join(UPLOAD_FOLDER, filename)

                        with open(assignment_file, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    # Ensure standard URL schema
                    clean_link = drive_link.strip()
                    if clean_link and not clean_link.startswith(("http://", "https://")):
                        clean_link = f"https://{clean_link}"

                    execute(
                        """
                        INSERT INTO homework (
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

                    st.success("Homework assigned successfully!")
                    st.rerun()

    # --------------------------------------
    # TAB 2: REVIEW SUBMISSIONS
    # --------------------------------------
    with tab2:
        st.subheader("Review & Grade Submissions")

        submissions = query_dataframe(
            """
            SELECT
                h.id,
                COALESCE(h.title, 'Untitled') AS title,
                s.first_name || ' ' || s.last_name AS student_name,
                h.assignment_file,
                h.student_file,
                h.file_link,
                COALESCE(h.status, 'Assigned') AS status,
                COALESCE(h.teacher_feedback, '') AS teacher_feedback,
                COALESCE(h.grade, '') AS grade,
                COALESCE(h.created_at::text, '') AS created_at
            FROM homework h
            JOIN students s ON h.student_id = s.id
            ORDER BY h.created_at DESC
            """
        )

        if submissions.empty:
            st.info("No homework submissions found.")
        else:
            submission_map = {
                f"#{row['id']} - {row['student_name']} — {row['title']} ({row['status']})": row["id"]
                for _, row in submissions.iterrows()
            }

            selected_sub_label = st.selectbox(
                "Select Homework Record",
                options=list(submission_map.keys())
            )

            selected_id = submission_map[selected_sub_label]
            selected = submissions[submissions["id"] == selected_id].iloc[0]

            st.info(
                f"**Student:** {selected['student_name']}  \n"
                f"**Title:** {selected['title']}  \n"
                f"**Status:** {selected['status']}"
            )

            grade_options = ["", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
            current_grade = str(selected["grade"]) if pd.notna(selected["grade"]) else ""
            default_grade_idx = grade_options.index(current_grade) if current_grade in grade_options else 0

            grade = st.selectbox(
                "Letter Grade",
                options=grade_options,
                index=default_grade_idx
            )

            feedback = st.text_area(
                "Teacher Feedback",
                value=selected["teacher_feedback"] if pd.notna(selected["teacher_feedback"]) else ""
            )

            if st.button("💾 Save Feedback & Grade", type="primary"):
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
                    (feedback.strip(), grade, int(selected_id))
                )
                st.success("Feedback saved successfully.")
                st.rerun()

            st.divider()
            st.subheader("Storage & File Management")

            col_f1, col_f2 = st.columns(2)

            with col_f1:
                if selected["assignment_file"] and os.path.exists(selected["assignment_file"]):
                    st.success("Assignment PDF on disk")
                    if st.button("🗑️ Delete Assignment PDF", key="del_assign_pdf"):
                        try:
                            os.remove(selected["assignment_file"])
                        except FileNotFoundError:
                            pass

                        execute(
                            "UPDATE homework SET assignment_file = NULL, deleted_assignment_file = 1 WHERE id = %s",
                            (int(selected_id),)
                        )
                        st.success("Assignment PDF removed.")
                        st.rerun()
                else:
                    st.caption("No original assignment file attached.")

            with col_f2:
                if selected["student_file"] and os.path.exists(selected["student_file"]):
                    st.success("Student submission on disk")
                    if st.button("🗑️ Delete Student Submission", key="del_student_pdf"):
                        try:
                            os.remove(selected["student_file"])
                        except FileNotFoundError:
                            pass

                        execute(
                            "UPDATE homework SET student_file = NULL, deleted_student_file = 1 WHERE id = %s",
                            (int(selected_id),)
                        )
                        st.success("Student submission file removed.")
                        st.rerun()
                else:
                    st.caption("No student submission file uploaded yet.")


# ==========================================
# STUDENT HOMEWORK PORTAL
# ==========================================

def student_homework():
    user = st.session_state.get("user", {})
    student_id = user.get("student_id")

    if not student_id:
        st.error("Student profile missing from session. Please log in again.")
        return

    st.header("📖 My Homework")

    ensure_homework_schema()

    homework = query_dataframe(
        """
        SELECT
            id,
            COALESCE(title, '') AS title,
            COALESCE(curriculum_topic, '') AS curriculum_topic,
            COALESCE(assigned_date::text, '') AS assigned_date,
            COALESCE(due_date::text, '') AS due_date,
            COALESCE(priority, 'Normal') AS priority,
            assignment_file,
            student_file,
            file_link,
            comment,
            teacher_feedback,
            grade,
            COALESCE(status, 'Assigned') AS status,
            COALESCE(created_at::text, '') AS created_at
        FROM homework
        WHERE student_id = %s
        ORDER BY created_at DESC
        """,
        (student_id,)
    )

    if homework.empty:
        st.info("No homework assigned yet.")
        return

    # Render Assigned Tasks
    for _, row in homework.iterrows():
        with st.container(border=True):
            st.subheader(row["title"] or f"Homework #{row['id']}")

            col1, col2 = st.columns(2)
            with col1:
                st.write("📚 **Topic:**", row["curriculum_topic"] or "N/A")
                st.write("📅 **Assigned:**", row["assigned_date"])
                st.write("⏰ **Due:**", row["due_date"])

            with col2:
                st.write("Priority:", row["priority"])

                if row["status"] == "Assigned":
                    st.warning("🟡 Waiting for submission")
                elif row["status"] == "Submitted":
                    st.info("🔵 Submitted — Awaiting grading")
                elif row["status"] == "Reviewed":
                    st.success("🟢 Graded")

                if pd.notna(row["grade"]) and row["grade"]:
                    st.success(f"**Grade:** {row['grade']}")

            if row["comment"]:
                st.write("**Instructions:**")
                st.info(row["comment"])

            # Safe download handling
            if row["assignment_file"]:
                if os.path.exists(row["assignment_file"]):
                    with open(row["assignment_file"], "rb") as f:
                        st.download_button(
                            "📥 Download Assignment File",
                            f,
                            file_name=os.path.basename(row["assignment_file"]),
                            key=f"dl_assign_{row['id']}"
                        )
                else:
                    st.warning("⚠️ Original assignment file is no longer on the server.")

            if row["file_link"]:
                st.link_button("🔗 Open Assignment Link", row["file_link"])

            if row["teacher_feedback"]:
                st.write("**Teacher Feedback:**")
                st.success(row["teacher_feedback"])

    st.divider()

    # Submit Completed Homework Section
    st.subheader("📤 Submit Completed Homework")

    active_assignments = homework[homework["status"] != "Reviewed"]

    if active_assignments.empty:
        st.info("No pending homework to submit.")
        return

    assignment_options = {
        f"#{row['id']} - {row['title'] or 'Untitled'} (Due: {row['due_date']})": row["id"]
        for _, row in active_assignments.iterrows()
    }

    selected_label = st.selectbox("Select Homework Assignment", list(assignment_options.keys()))
    selected_assignment_id = assignment_options[selected_label]

    upload = st.file_uploader(
        "Upload Solution (PDF or Image)",
        type=["pdf", "jpg", "jpeg", "png"],
        key="student_solution_upload"
    )

    if st.button("Submit Homework", type="primary"):
        if not upload:
            st.error("Please select a file to upload before submitting.")
        else:
            filename = f"student_{student_id}_{selected_assignment_id}_{upload.name}"
            student_file = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            with open(student_file, "wb") as f:
                f.write(upload.getbuffer())

            execute(
                """
                UPDATE homework
                SET
                    student_file = %s,
                    status = 'Submitted',
                    submitted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND student_id = %s
                """,
                (student_file, int(selected_assignment_id), student_id)
            )

            st.success("Homework submitted successfully!")
            st.rerun()
