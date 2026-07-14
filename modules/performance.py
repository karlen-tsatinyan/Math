import streamlit as st
import pandas as pd

from database import query_dataframe


def performance_dashboard():

    st.title("📈 Performance Progression Tracking")

    students = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        ORDER BY last_name
        """
    )

    if len(students) == 0:
        st.warning("No students found.")
        return

    # -----------------------------
    # Remember selected student
    # -----------------------------

    selected_student_id = st.session_state.get("selected_student")

    student_names = students["name"].tolist()

    default_index = 0

    if selected_student_id is not None:

        match = students[
            students["id"] == selected_student_id
        ]

        if len(match) > 0:
            default_index = match.index[0]

    student_name = st.selectbox(

        "Student",

        student_names,

        index=default_index

    )

    student_id = int(

        students[
            students["name"] == student_name
        ]["id"].iloc[0]

    )

    st.session_state.selected_student = student_id

    grades = query_dataframe(
        """
        SELECT

            lesson_date,

            topic,

            score,

            max_score,

            percent,

            grade_letter,

            teacher_comment

        FROM homework_grades

        WHERE student_id=?

        ORDER BY lesson_date

        """,
        (student_id,)
    )

    if len(grades) == 0:

        st.info("No graded homework yet.")

        return

    tab1, tab2 = st.tabs(

        [

            "Dashboard",

            "Grade History"

        ]

    )

    with tab1:

        average = grades["percent"].mean()

        highest = grades["percent"].max()

        lowest = grades["percent"].min()

        improvement = (
            grades.iloc[-1]["percent"]
            -
            grades.iloc[0]["percent"]
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(

            "Average",

            f"{average:.1f}%"

        )

        c2.metric(

            "Highest",

            f"{highest:.1f}%"

        )

        c3.metric(

            "Lowest",

            f"{lowest:.1f}%"

        )

        c4.metric(

            "Trend",

            f"{improvement:+.1f}%"

        )

        st.subheader(

            "Chronological Score Variance"

        )

        chart = grades.set_index(

            "lesson_date"

        )[

            "percent"

        ]

        st.line_chart(chart)

    with tab2:

        st.dataframe(

            grades,

            use_container_width=True,

            hide_index=True

        )