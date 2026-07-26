import streamlit as st
import os
import pandas as pd
from datetime import date
from database import execute, query_dataframe
from config import UPLOAD_FOLDER

# ============================================================
# HELPER: SAFE VALUE
# ============================================================
def safe_text(value):
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()

# ============================================================
# ADMIN HOMEWORK MANAGEMENT
# ============================================================
def homework_management():
    st.header("Teacher Homework Management")
    tab1, tab2 = st.tabs(["Assign Homework", "Review & Grade Submissions"])

    # ========================================================
    # GET STUDENTS
    # ========================================================
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
        st.warning("No students available.")
        return

    selected_student_id = st.session_state.get("selected_student")
    student_names = students["name"].tolist()
    default_index = 0
    if selected_student_id is not None:
        match = students[students["id"] == selected_student_id]
        if not match.empty:
            default_index = match.index[0]

    # ========================================================
    # TAB 1 — ASSIGN HOMEWORK
    # ========================================================
    with tab1:
        st.subheader("Assign New Homework")
        student_name = st.selectbox("Student", student_names, index=default_index, key="assign_student")
        student_id = int(students[students["name"] == student_name]["id"].iloc[0])
        st.session_state.selected_student = student_id

        title = st.text_input("Homework Title", key="homework_title")
        curriculum = st.text_input("Curriculum Topic", key="homework_curriculum")
        assigned_date = st.date_input("Assigned Date", value=date.today(), key="homework_assigned_date")
        due_date = st.date_input("Due Date", key="homework_due_date")
        priority = st.selectbox("Priority", ["Normal", "Important"], key="homework_priority")
        uploaded_file = st.file_uploader("Upload Assignment", type=["pdf", "jpg", "jpeg", "png"], key="teacher_upload")
        drive_link = st.text_input("Google Drive Link", key="homework_drive_link")
        comment = st.text_area("Instructions / Comments", key="homework_comment")
        st.divider()

        if st.button("➕ Assign Homework", key="assign_homework_button"):
            if not title.strip():
                st.error("Please enter a Homework Title.")
                return
            if not uploaded_file and not drive_link.strip():
                st.error("Please upload an assignment PDF/image or provide a Google Drive link.")
                return

            file_path = None
            # ------------------------------------------------
            # SAVE ASSIGNMENT FILE
            # ------------------------------------------------
            if uploaded_file:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(
                    UPLOAD_FOLDER,
                    f"{student_id}_{date.today()}_{uploaded_file.name}"
                )
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            # ------------------------------------------------
            # INSERT HOMEWORK
            # ------------------------------------------------
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
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            st.success("✅ Homework assigned successfully.")
            st.cache_data.clear()

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
            st.info("No homework submissions found.")
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
            submissions[display_columns].rename(
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
            homework_options[label] = int(row["id"])

        selected_label = st.selectbox("Select Homework to Review", list(homework_options.keys()), key="review_homework_select")
        selected_id = homework_options[selected_label]
        selected_rows = submissions[submissions["id"] == selected_id]
        if selected_rows.empty:
            st.error("Unable to find the selected homework.")
            return

        selected = selected_rows.iloc[0]

        # ====================================================
        # HOMEWORK INFORMATION
        # ====================================================
        st.subheader(f"📚 {safe_text(selected['title'])}")
        info1, info2, info3 = st.columns(3)
        with info1:
            st.write("**Student:**", safe_text(selected["student_name"]))
        with info2:
            st.write("**Due Date:**", safe_text(selected["due_date"]))
        with info3:
            st.write("**Status:**", safe_text(selected["status"]))

        if safe_text(selected["curriculum_topic"]):
            st.write("**Curriculum Topic:**", safe_text(selected["curriculum_topic"]))
        if safe_text(selected["comment"]):
            st.info("Instructions: " + safe_text(selected["comment"]))

        # ====================================================
        # ORIGINAL ASSIGNMENT
        # ====================================================
        st.divider()
        st.subheader("📄 Original Assignment")
        assignment_file = selected["assignment_file"]
        assignment_link = selected["file_link"]
        assignment_deleted = selected["deleted_assignment_file"]

        if pd.notna(assignment_deleted) and int(assignment_deleted) == 1:
            st.warning("The original assignment file has been deleted.")
        elif pd.notna(assignment_file) and str(assignment_file).strip():
            assignment_file = str(assignment_file).strip()
            if os.path.exists(assignment_file):
                with open(assignment_file, "rb") as f:
                    assignment_data = f.read()
                st.download_button(
                    "📥 Open / Download Assignment",
                    data=assignment_data,
                    file_name=os.path.basename(assignment_file),
                    mime="application/pdf",
                    key=f"assignment_download_{int(selected_id)}"
                )
                st.caption("Click the button to open/download the original assignment.")
            else:
                st.warning("The original assignment file is no longer available on the server.")
        elif pd.notna(assignment_link) and str(assignment_link).strip():
            st.link_button("🔗 Open Google Drive Assignment", str(assignment_link).strip())
        else:
            st.info("No original assignment file or link is available.")

        # ====================================================
        # DELETE ORIGINAL ASSIGNMENT
        # ====================================================
        if pd.notna(assignment_file) and str(assignment_file).strip() and int(selected["deleted_assignment_file"] or 0) == 0:
            if st.button("🗑 Delete Assignment File", key=f"delete_assignment_{int(selected_id)}"):
                assignment_path = str(assignment_file).strip()
                if os.path.exists(assignment_path):
                    try:
                        os.remove(assignment_path)
                    except Exception as e:
                        st.warning(f"Could not delete physical file: {e}")
                execute(
                    """
                    UPDATE homework
                    SET
                        assignment_file=NULL,
                        deleted_assignment_file=1
                    WHERE id=%s
                    """,
                    (int(selected_id),)
                )
                st.success("Assignment file deleted.")
                st.cache_data.clear()
                st.rerun()

        # ====================================================
        # STUDENT SUBMISSION
        # ====================================================
        st.divider()
        st.subheader("📝 Student Submission")
        student_file = selected["student_file"]
        student_deleted = selected["deleted_student_file"]

        if pd.notna(student_deleted) and int(student_deleted) == 1:
            st.warning("The student's submitted file has been deleted.")
        elif pd.notna(student_file) and str(student_file).strip():
            student_file = str(student_file).strip()
            if os.path.exists(student_file):
                with open(student_file, "rb") as f:
                    student_data = f.read()
                st.download_button(
                    "📥 Open / Download Student Work",
                    data=student_data,
                    file_name=os.path.basename(student_file),
                    mime="application/pdf",
                    key=f"student_download_{int(selected_id)}"
                )
                st.caption("Download/open the student's completed homework to review.")
            else:
                st.warning("The student's submitted file is no longer available on the server.")
        else:
            st.info("No student submission is available.")

        # ====================================================
        # DELETE STUDENT SUBMISSION
        # ====================================================
        if pd.notna(student_file) and str(student_file).strip() and int(selected["deleted_student_file"] or 0) == 0:
            if st.button("🗑 Delete Student Submission", key=f"delete_student_file_{int(selected_id)}"):
                student_path = str(student_file).strip()
                if os.path.exists(student_path):
                    try:
                        os.remove(student_path)
                    except Exception as e:
                        st.warning(f"Could not delete physical file: {e}")
                execute(
                    """
                    UPDATE homework
                    SET
                        student_file=NULL,
                        deleted_student_file=1
                    WHERE id=%s
                    """,
                    (int(selected_id),)
                )
                st.success("Student submission deleted.")
                st.cache_data.clear()
                st.rerun()

        # ====================================================
        # GRADE & FEEDBACK
        # ====================================================
        st.divider()
        st.subheader("📝 Grade & Teacher Feedback")
        grade_options = ["", "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
        current_grade = safe_text(selected["grade"])
        if current_grade not in grade_options:
            current_grade = ""

        grade = st.selectbox("Letter Grade", grade_options, index=grade_options.index(current_grade), key=f"grade_select_{int(selected_id)}")
        current_feedback = safe_text(selected["teacher_feedback"])
        feedback = st.text_area("Teacher Feedback", value=current_feedback, key=f"feedback_{int(selected_id)}")

        if st.button("💾 Save Grade & Feedback", key=f"save_grade_{int(selected_id)}"):
            execute(
                """
                UPDATE homework
                SET
                    teacher_feedback=%s,
                    grade=%s,
                    status='Reviewed',
                    reviewed_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (feedback.strip(), grade, int(selected_id))
            )
            st.success("✅ Grade and feedback saved.")
            st.cache_data.clear()
            st.rerun()

# ============================================================
# STUDENT HOMEWORK PORTAL
# ============================================================
def student_homework():
    student_id = st.session_state.user["student_id"]
    st.header("My Homework")
    homework = query_dataframe(
        """
        SELECT
            id,
            title,
            curriculum_topic,
            assigned_date,
            due_date,
            priority,
            assignment_file,
            student_file,
            file_link,
            comment,
            teacher_feedback,
            grade,
            status,
            deleted_assignment_file,
            deleted_student_file,
            submitted_at,
            reviewed_at,
            created_at
        FROM homework
        WHERE student_id=%s
        ORDER BY created_at DESC
        """,
        (student_id,)
    )
    if homework.empty:
        st.info("No homework assigned.")
        return

    # ========================================================
    # DISPLAY HOMEWORK
    # ========================================================
    for _, row in homework.iterrows():
        title = safe_text(row["title"])
        st.subheader(title if title else f"Homework #{int(row['id'])}")
        col1, col2 = st.columns(2)
        with col1:
            st.write("📚 Topic:", safe_text(row["curriculum_topic"]))
            st.write("📅 Assigned:", safe_text(row["assigned_date"]))
            st.write("⏰ Due:", safe_text(row["due_date"]))
        with col2:
            st.write("Priority:", safe_text(row["priority"]))
            st.write("Status:", safe_text(row["status"]))
            grade = safe_text(row["grade"])
            if grade:
                st.success(f"Grade: {grade}")

        # ----------------------------------------------------
        # INSTRUCTIONS
        # ----------------------------------------------------
        comment = safe_text(row["comment"])
        if comment:
            st.write("**Instructions:**")
            st.info(comment)

        # ----------------------------------------------------
        # ORIGINAL ASSIGNMENT
        # ----------------------------------------------------
        assignment_file = safe_text(row["assignment_file"])
        assignment_link = safe_text(row["file_link"])
        assignment_deleted = int(row["deleted_assignment_file"] or 0)

        if assignment_deleted == 0:
            if assignment_file:
                if os.path.exists(assignment_file):
                    with open(assignment_file, "rb") as f:
                        assignment_data = f.read()
                    st.download_button(
                        "📥 Open / Download Assignment",
                        data=assignment_data,
                        file_name=os.path.basename(assignment_file),
                        mime="application/pdf",
                        key=f"student_assignment_{int(row['id'])}"
                    )
                else:
                    st.warning("Assignment file is not currently available.")
            elif assignment_link:
                st.link_button("🔗 Open Google Drive Assignment", assignment_link)

        # ----------------------------------------------------
        # TEACHER FEEDBACK
        # ----------------------------------------------------
        teacher_feedback = safe_text(row["teacher_feedback"])
        if teacher_feedback:
            st.success("👩‍🏫 Teacher Feedback: " + teacher_feedback)
        st.divider()

    # ========================================================
    # STUDENT SUBMISSION
    # ========================================================
    st.subheader("📤 Submit Completed Homework")
    selectable_homework = homework[homework["status"].isin(["Assigned", "Submitted", "Reviewed"])]
    if selectable_homework.empty:
        st.info("There are no assignments available for submission.")
        return

    assignment_labels = {}
    for _, row in selectable_homework.iterrows():
        label = f"#{int(row['id'])} — {safe_text(row['title'])}"
        assignment_labels[label] = int(row["id"])

    selected_assignment_label = st.selectbox("Assignment", list(assignment_labels.keys()), key="student_assignment_select")
    selected_assignment_id = assignment_labels[selected_assignment_label]
    upload = st.file_uploader("Upload Your Solution", type=["pdf", "jpg", "jpeg", "png"], key="student_homework_upload")

    if st.button("📤 Submit Homework", key="submit_homework_button"):
        if not upload:
            st.error("Please upload your completed homework first.")
            return

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        path = os.path.join(UPLOAD_FOLDER, f"student_{student_id}_{selected_assignment_id}_{upload.name}")
        with open(path, "wb") as f:
            f.write(upload.getbuffer())

        execute(
            """
            UPDATE homework
            SET
                student_file=%s,
                status='Submitted',
                submitted_at=CURRENT_TIMESTAMP,
                deleted_student_file=0
            WHERE id=%s
              AND student_id=%s
            """,
            (path, selected_assignment_id, student_id)
        )
        st.success("✅ Homework submitted successfully.")
        st.cache_data.clear()
        st.rerun()
