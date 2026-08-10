import streamlit as st
import pandas as pd

from database import query_dataframe


# ============================================================
# PERFORMANCE PROGRESSION DASHBOARD
# ============================================================

def performance_dashboard():
    st.title("📈 Performance Progression Tracking")

    # --------------------------------------------------------
    # STUDENT SELECTION
    # --------------------------------------------------------
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

    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"]
        for _, row in students.iterrows()
    }

    saved_student_id = st.session_state.get("selected_student_id")
    default_index = 0

    if saved_student_id:
        for idx, (_, s_id) in enumerate(student_options.items()):
            if s_id == saved_student_id:
                default_index = idx
                break

    selected_label = st.selectbox(
        "Select Student",
        options=list(student_options.keys()),
        index=default_index,
    )

    student_id = student_options[selected_label]
    st.session_state.selected_student_id = student_id

    # --------------------------------------------------------
    # GRADED HOMEWORK
    #
    # IMPORTANT:
    # due_date is the academic progression date.
    # reviewed_at / submitted_at are deliberately NOT used
    # for the progression timeline.
    # --------------------------------------------------------
    grades = query_dataframe(
        """
        SELECT
            due_date::text AS lesson_date,

            COALESCE(
                curriculum_topic,
                title,
                'Homework Assignment'
            ) AS topic,

            title AS homework_title,

            100 AS max_score,

            CASE
                WHEN grade = 'A+' THEN 98
                WHEN grade = 'A'  THEN 95
                WHEN grade = 'A-' THEN 92
                WHEN grade = 'B+' THEN 88
                WHEN grade = 'B'  THEN 85
                WHEN grade = 'B-' THEN 82
                WHEN grade = 'C+' THEN 78
                WHEN grade = 'C'  THEN 75
                WHEN grade = 'C-' THEN 72
                WHEN grade = 'D'  THEN 65
                WHEN grade = 'F'  THEN 50
                ELSE 0
            END AS percent,

            grade AS grade_letter,

            COALESCE(
                teacher_feedback,
                ''
            ) AS teacher_comment

        FROM homework

        WHERE student_id = %s
          AND status = 'Reviewed'
          AND due_date IS NOT NULL

        ORDER BY due_date ASC, id ASC
        """,
        (student_id,)
    )

    if grades.empty:
        st.info(
            "No graded homework with due dates was found for this student."
        )
        return

    # --------------------------------------------------------
    # DATA CLEANUP / SORTING
    # --------------------------------------------------------
    grades["lesson_date"] = pd.to_datetime(
        grades["lesson_date"],
        errors="coerce"
    )

    grades["percent"] = pd.to_numeric(
        grades["percent"],
        errors="coerce"
    ).fillna(0)

    grades = grades.sort_values(
        by=["lesson_date"],
        ascending=True
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------
    tab1, tab2 = st.tabs(
        ["Dashboard", "Grade History"]
    )

    # ========================================================
    # TAB 1 — DASHBOARD
    # ========================================================
    with tab1:

        average = grades["percent"].mean()
        highest = grades["percent"].max()
        lowest = grades["percent"].min()

        if len(grades) > 1:
            improvement = (
                grades.iloc[-1]["percent"]
                - grades.iloc[0]["percent"]
            )
            trend_str = f"{improvement:+.1f}%"
        else:
            trend_str = "Baseline (1 Entry)"

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Average Score",
            f"{average:.1f}%"
        )

        c2.metric(
            "Highest Score",
            f"{highest:.1f}%"
        )

        c3.metric(
            "Lowest Score",
            f"{lowest:.1f}%"
        )

        c4.metric(
            "Overall Trend",
            trend_str
        )

        st.divider()

        st.subheader(
            "📊 Advanced Progression Analytics"
        )

        st.caption(
            "Progression is plotted by homework due date, "
            "not by the date the homework was submitted or graded."
        )

        chart_data = grades.dropna(
            subset=["lesson_date"]
        ).copy()

        chart_data["formatted_date"] = (
            chart_data["lesson_date"]
            .dt.strftime("%Y-%m-%d")
        )

        if not chart_data.empty:

            try:
                import altair as alt

                base = alt.Chart(
                    chart_data
                ).encode(
                    x=alt.X(
                        "formatted_date:N",
                        title="Homework Due Date",
                        sort=None
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "formatted_date:N",
                            title="Due Date"
                        ),
                        alt.Tooltip(
                            "homework_title:N",
                            title="Homework"
                        ),
                        alt.Tooltip(
                            "topic:N",
                            title="Topic"
                        ),
                        alt.Tooltip(
                            "percent:Q",
                            title="Score (%)",
                            format=".1f"
                        ),
                        alt.Tooltip(
                            "grade_letter:N",
                            title="Grade"
                        )
                    ]
                )

                line = base.mark_line(
                    strokeWidth=3
                ).encode(
                    y=alt.Y(
                        "percent:Q",
                        title="Score Percentage (%)",
                        scale=alt.Scale(
                            domain=[0, 100]
                        )
                    )
                )

                points = base.mark_circle(
                    size=80
                ).encode(
                    y=alt.Y(
                        "percent:Q",
                        title="Score Percentage (%)",
                        scale=alt.Scale(
                            domain=[0, 100]
                        )
                    )
                )

                chart = (
                    line + points
                ).interactive().properties(
                    height=380
                )

                st.altair_chart(
                    chart,
                    use_container_width=True
                )

            except Exception:
                fallback_df = (
                    chart_data[
                        ["lesson_date", "percent"]
                    ]
                    .set_index("lesson_date")
                )

                fallback_df.rename(
                    columns={
                        "percent": "Score (%)"
                    },
                    inplace=True
                )

                st.area_chart(
                    fallback_df
                )

        else:
            st.info(
                "No valid due dates found to render progression chart."
            )

    # ========================================================
    # TAB 2 — GRADE HISTORY
    # ========================================================
    with tab2:

        st.subheader(
            "📋 Historical Records"
        )

        display_df = grades.copy()

        if pd.api.types.is_datetime64_any_dtype(
            display_df["lesson_date"]
        ):
            display_df["lesson_date"] = (
                display_df["lesson_date"]
                .dt.strftime("%Y-%m-%d")
            )

        display_df = display_df.rename(
            columns={
                "lesson_date": "Due Date",
                "homework_title": "Homework",
                "topic": "Topic",
                "percent": "Percentage",
                "grade_letter": "Grade",
                "teacher_comment": "Teacher Comments"
            }
        )

        columns_to_show = [
            "Due Date",
            "Homework",
            "Topic",
            "Percentage",
            "Grade",
            "Teacher Comments"
        ]

        display_df = display_df[
            [
                col
                for col in columns_to_show
                if col in display_df.columns
            ]
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Percentage": st.column_config.NumberColumn(
                    "Percentage",
                    format="%.1f%%"
                )
            }
        )


# ============================================================
# STUDENT PERFORMANCE VIEW
# Used by Student Portal
# ============================================================

def student_performance_view(student_id):

    st.subheader(
        "📈 Advanced Progression Analytics"
    )

    grades = query_dataframe(
        """
        SELECT
            due_date::text AS lesson_date,

            COALESCE(
                curriculum_topic,
                title,
                'Homework Assignment'
            ) AS topic,

            title AS homework_title,

            CASE
                WHEN grade = 'A+' THEN 98
                WHEN grade = 'A'  THEN 95
                WHEN grade = 'A-' THEN 92
                WHEN grade = 'B+' THEN 88
                WHEN grade = 'B'  THEN 85
                WHEN grade = 'B-' THEN 82
                WHEN grade = 'C+' THEN 78
                WHEN grade = 'C'  THEN 75
                WHEN grade = 'C-' THEN 72
                WHEN grade = 'D'  THEN 65
                WHEN grade = 'F'  THEN 50
                ELSE 0
            END AS percent,

            grade AS grade_letter,

            COALESCE(
                teacher_feedback,
                ''
            ) AS teacher_comment

        FROM homework

        WHERE student_id = %s
          AND status = 'Reviewed'
          AND due_date IS NOT NULL

        ORDER BY due_date ASC, id ASC
        """,
        (student_id,)
    )

    if grades.empty:
        st.info(
            "No performance data available yet."
        )
        return

    grades["lesson_date"] = pd.to_datetime(
        grades["lesson_date"],
        errors="coerce"
    )

    grades["percent"] = pd.to_numeric(
        grades["percent"],
        errors="coerce"
    ).fillna(0)

    grades = grades.sort_values(
        by=["lesson_date"],
        ascending=True
    ).reset_index(drop=True)

    chart_data = grades.dropna(
        subset=["lesson_date"]
    ).copy()

    if chart_data.empty:
        st.info(
            "No valid due dates available for chart."
        )
        return

    chart_data["formatted_date"] = (
        chart_data["lesson_date"]
        .dt.strftime("%Y-%m-%d")
    )

    st.caption(
        "Progression is plotted by homework due date, "
        "not by submission or grading date."
    )

    try:
        import altair as alt

        chart = (
            alt.Chart(chart_data)
            .mark_line(
                point=True
            )
            .encode(
                x=alt.X(
                    "formatted_date:N",
                    title="Homework Due Date",
                    sort=None
                ),
                y=alt.Y(
                    "percent:Q",
                    title="Score (%)",
                    scale=alt.Scale(
                        domain=[0, 100]
                    )
                ),
                tooltip=[
                    alt.Tooltip(
                        "formatted_date:N",
                        title="Due Date"
                    ),
                    alt.Tooltip(
                        "homework_title:N",
                        title="Homework"
                    ),
                    alt.Tooltip(
                        "topic:N",
                        title="Topic"
                    ),
                    alt.Tooltip(
                        "percent:Q",
                        title="Score (%)",
                        format=".1f"
                    ),
                    alt.Tooltip(
                        "grade_letter:N",
                        title="Grade"
                    )
                ]
            )
            .interactive()
            .properties(
                height=380
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True
        )

    except Exception:

        fallback = (
            chart_data[
                [
                    "lesson_date",
                    "percent"
                ]
            ]
            .set_index("lesson_date")
        )

        st.line_chart(
            fallback
        )
