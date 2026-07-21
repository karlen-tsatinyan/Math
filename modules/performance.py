import pandas as pd
import streamlit as st

from database import execute, query_dataframe


def ensure_performance_schema():
    """Ensure homework_grades table exists with all required columns in PostgreSQL/SQLite."""
    try:
        execute(
            """
            CREATE TABLE IF NOT EXISTS homework_grades (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                lesson_date DATE DEFAULT CURRENT_DATE,
                topic TEXT,
                score NUMERIC(5,2),
                max_score NUMERIC(5,2) DEFAULT 100,
                percent NUMERIC(5,2),
                grade_letter TEXT,
                teacher_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    except Exception:
        pass


def performance_dashboard():
    st.title("📈 Performance Progression Tracking")

    # Run auto-migration check for performance table
    ensure_performance_schema()

    # Fetch active students
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
        st.warning("No students available. Please enroll students first.")
        return

    # Safe student selection map { "Jane Smith (ID: 12)": 12 }
    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"]
        for _, row in students.iterrows()
    }

    # Session state index memory
    saved_student_id = st.session_state.get("selected_student_id")
    default_index = 0

    if saved_student_id:
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

    # Query grades using PostgreSQL %s placeholder
    grades = query_dataframe(
        """
        SELECT
            lesson_date::text AS lesson_date,
            topic,
            score,
            max_score,
            percent,
            grade_letter,
            teacher_comment
        FROM homework_grades
        WHERE student_id = %s
        ORDER BY lesson_date ASC
        """,
        (student_id,)
    )

    if grades.empty:
        st.info("No graded homework or performance records found for this student.")
        return

    # Convert lesson_date to datetime objects for proper chronological chart ordering
    grades["lesson_date"] = pd.to_datetime(grades["lesson_date"])
    grades["percent"] = pd.to_numeric(grades["percent"], errors="coerce").fillna(0)

    tab1, tab2 = st.tabs(["Dashboard", "Grade History"])

    # =========================================================
    # TAB 1: DASHBOARD
    # =========================================================
    with tab1:
        average = grades["percent"].mean()
        highest = grades["percent"].max()
        lowest = grades["percent"].min()

        # Calculate trend safely
        if len(grades) > 1:
            improvement = grades.iloc[-1]["percent"] - grades.iloc[0]["percent"]
            trend_str = f"{improvement:+.1f}%"
        else:
            trend_str = "Baseline (1 Entry)"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Average Score", f"{average:.1f}%")
        c2.metric("Highest Score", f"{highest:.1f}%")
        c3.metric("Lowest Score", f"{lowest:.1f}%")
        c4.metric("Overall Trend", trend_str)

        st.divider()
        st.subheader("📊 Chronological Score Variance")

        # Prepare line chart data
        chart_df = grades[["lesson_date", "percent"]].set_index("lesson_date")
        chart_df.rename(columns={"percent": "Score (%)"}, inplace=True)

        st.line_chart(chart_df)

    # =========================================================
    # TAB 2: GRADE HISTORY
    # =========================================================
    with tab2:
        st.subheader("📋 Historical Records")

        # Display nicely formatted dataframe
        display_df = grades.copy()
        display_df["lesson_date"] = display_df["lesson_date"].dt.strftime("%Y-%m-%d")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "lesson_date": "Lesson Date",
                "topic": "Topic",
                "score": "Score",
                "max_score": "Max Score",
                "percent": st.column_config.NumberColumn("Percentage", format="%.1f%%"),
                "grade_letter": "Grade",
                "teacher_comment": "Teacher Comments"
            }
        )
