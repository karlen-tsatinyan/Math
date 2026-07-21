import streamlit as st
from database import execute, query_dataframe


def progress_management():
    st.title("📈 Student Progress Notes")

    # Fetch students
    students = query_dataframe(
        """
        SELECT 
            id, 
            first_name || ' ' || last_name AS name 
        FROM students 
        ORDER BY last_name
        """
    )

    if students.empty:
        st.warning("No students available. Please enroll students first.")
        return

    # Build reliable student map { "John Doe (ID: 4)": 4 } to handle duplicate names safely
    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"] 
        for _, row in students.iterrows()
    }
    
    # Session state index memory
    saved_student_id = st.session_state.get("selected_student_id")
    default_index = 0

    if saved_student_id:
        # Find index matching current ID
        for idx, (label, s_id) in enumerate(student_options.items()):
            if s_id == saved_student_id:
                default_index = idx
                break

    selected_label = st.selectbox(
        "Select Student",
        options=list(student_options.keys()),
        index=default_index
    )

    student_id = student_options[selected_label]
    st.session_state.selected_student_id = student_id

    tab1, tab2 = st.tabs(["➕ Add Note", "📖 View History"])

    # =========================================================
    # TAB 1: ADD NOTE
    # =========================================================
    with tab1:
        with st.form("progress_note_form", clear_on_submit=True):
            st.subheader("New Progress Entry")
            
            col1, col2 = st.columns(2)
            with col1:
                lesson_date = st.date_input("Lesson Date")
            with col2:
                topic = st.text_input("Lesson Topic", placeholder="e.g., Quadratic Equations / Scales")

            strengths = st.text_area("Strengths & Achievements", placeholder="What went well?")
            improvements = st.text_area("Needs Improvement / Focus Areas", placeholder="What needs practice?")
            homework = st.text_area("Homework Assigned", placeholder="Specific exercises or pages")
            next_steps = st.text_area("Plan for Next Lesson", placeholder="Goals for next session")

            submit_btn = st.form_submit_button("Save Progress Note", use_container_width=True)

            if submit_btn:
                if not topic.strip():
                    st.error("Please provide a lesson topic before saving.")
                else:
                    execute(
                        """
                        INSERT INTO progress_notes (
                            student_id, lesson_date, topic, strengths,
                            improvements, homework, next_steps
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            student_id,
                            str(lesson_date),
                            topic.strip(),
                            strengths.strip(),
                            improvements.strip(),
                            homework.strip(),
                            next_steps.strip()
                        )
                    )
                    st.success("Progress note saved successfully!")
                    st.rerun()

    # =========================================================
    # TAB 2: VIEW HISTORY
    # =========================================================
    with tab2:
        notes = query_dataframe(
            """
            SELECT
                id,
                lesson_date,
                topic,
                strengths,
                improvements,
                homework,
                next_steps
            FROM progress_notes
            WHERE student_id = ?
            ORDER BY lesson_date DESC
            """,
            (student_id,)
        )

        if notes.empty:
            st.info("No progress notes recorded for this student yet.")
        else:
            st.caption(f"Showing {len(notes)} note(s)")
            
            for _, note in notes.iterrows():
                header = f"📅 {note['lesson_date']} — {note['topic']}"
                
                with st.expander(header, expanded=False):
                    c1, c2 = st.columns(2)
                    with c1:
                        if note["strengths"]:
                            st.markdown(f"**💪 Strengths:**\n{note['strengths']}")
                        if note["improvements"]:
                            st.markdown(f"**🎯 Needs Work:**\n{note['improvements']}")
                    
                    with c2:
                        if note["homework"]:
                            st.markdown(f"**📚 Homework:**\n{note['homework']}")
                        if note["next_steps"]:
                            st.markdown(f"**🚀 Next Steps:**\n{note['next_steps']}")

                    st.divider()
                    
                    # Delete action
                    if st.button("🗑️ Delete Note", key=f"del_note_{note['id']}"):
                        execute("DELETE FROM progress_notes WHERE id = ?", (note["id"],))
                        st.success("Note removed.")
                        st.rerun()
