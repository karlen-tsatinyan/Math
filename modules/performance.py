import streamlit as st
import pandas as pd
from database import execute, query_dataframe

# ============================================================
# SCHEMA MIGRATION / INITIALIZATION (SUPABASE COMPATIBLE)
# ============================================================
def ensure_performance_schema():
    """Ensure homework_grades table exists AND contains all required columns for Supabase PostgreSQL."""
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

        columns_to_add = [
            ("lesson_date", "DATE DEFAULT CURRENT_DATE"),
            ("topic", "TEXT"),
            ("score", "NUMERIC(5,2)"),
            ("max_score", "NUMERIC(5,2) DEFAULT 100"),
            ("percent", "NUMERIC(5,2)"),
            ("grade_letter", "TEXT"),
            ("teacher_comment", "TEXT")
        ]

        for col_name, col_type in columns_to_add:
            try:
                execute(f"ALTER TABLE homework_grades ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
            except Exception:
                pass
    except Exception:
        pass

# ============================================================
# PERFORMANCE PROGRESSION DASHBOARD (SUPABASE ENVIRONMENT)
# ============================================================
def performance_dashboard():
    st.title("📈 Performance Progression Tracking")

    # Run auto-migration check for Supabase PostgreSQL schema
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

    # Safe student selection map
    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"]
        for _, row in students.iterrows()
    }

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

    # --------------------------------------------------------
    # UNIFIED GRADE QUERY (Supabase PostgreSQL Compatible)
    # --------------------------------------------------------
    grades = query_dataframe(
        """
        SELECT
            COALESCE(
                lesson_date::text,
                created_at::text,
                ''
            ) AS lesson_date,
    
            COALESCE(
                topic,
                'Homework Assignment'
            ) AS topic,
    
            COALESCE(score,0) AS score,
    
            COALESCE(max_score,100) AS max_score,
    
            COALESCE(percent,0) AS percent,
    
            COALESCE(
                grade_letter,
                ''
            ) AS grade_letter,
    
            COALESCE(
                teacher_comment,
                ''
            ) AS teacher_comment,
    
            'Archived Record' AS record_status
    
    
        FROM homework_grades
    
        WHERE student_id = %s
    
    
        ORDER BY lesson_date ASC
    
        """,
        (
            student_id,
        )
    )

    if grades.empty:
        st.info("No graded homework or performance records found for this student.")
        return

    # Process types for Supabase results
    grades["lesson_date"] = pd.to_datetime(grades["lesson_date"], errors="coerce")
    grades["percent"] = pd.to_numeric(grades["percent"], errors="coerce").fillna(0)

    tab1, tab2 = st.tabs(["Dashboard", "Grade History"])

    # =========================================================
    # TAB 1: DASHBOARD (Altair Interactive Fancy Charts)
    # =========================================================
    with tab1:
        average = grades["percent"].mean()
        highest = grades["percent"].max()
        lowest = grades["percent"].min()

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
        st.subheader("📊 Advanced Progression Analytics")

        chart_data = grades.dropna(subset=["lesson_date"]).copy()
        chart_data["formatted_date"] = chart_data["lesson_date"].dt.strftime("%Y-%m-%d")

        if not chart_data.empty:
            try:
                import altair as alt

                base = alt.Chart(chart_data).encode(
                    x=alt.X("formatted_date:N", title="Lesson Date", sort=None),
                    tooltip=[
                        alt.Tooltip("formatted_date:N", title="Date"),
                        alt.Tooltip("topic:N", title="Topic"),
                        alt.Tooltip("percent:Q", title="Score (%)", format=".1f"),
                        alt.Tooltip("grade_letter:N", title="Grade")
                    ]
                )

                area = base.mark_area(
                    line={"color": "#4C78A8"},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="#4C78A8", offset=0),
                            alt.GradientStop(color="rgba(76, 120, 168, 0.0)", offset=1)
                        ],
                        x1=1,
                        y1=1,
                        x2=1,
                        y2=0
                    ),
                    opacity=0.6
                )

                points = base.mark_circle(size=80, color="#1f77b4").encode(
                    y=alt.Y("percent:Q", title="Score Percentage (%)", scale=alt.Scale(domain=[0, 100]))
                )

                line = base.mark_line(strokeWidth=3, color="#1f77b4").encode(
                    y=alt.Y("percent:Q", scale=alt.Scale(domain=[0, 100]))
                )

                chart = (area + line + points).interactive().properties(
                    height=380
                )

                st.altair_chart(chart, use_container_width=True)
            except Exception:
                fallback_df = chart_data[["lesson_date", "percent"]].set_index("lesson_date")
                fallback_df.rename(columns={"percent": "Score (%)"}, inplace=True)
                st.area_chart(fallback_df)
        else:
            st.info("No valid dates found to render progression chart.")

    # =========================================================
    # TAB 2: GRADE HISTORY
    # =========================================================
    with tab2:
        st.subheader("📋 Historical Records")

        display_df = grades.copy()
        if pd.api.types.is_datetime64_any_dtype(display_df["lesson_date"]):
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

# ============================================================
# STUDENT PERFORMANCE VIEW
# Used by Student Portal
# ============================================================

def student_performance_view(student_id):

    ensure_performance_schema()

    st.subheader("📈 Advanced Progression Analytics")


    grades = query_dataframe(
        """
        SELECT
    
            COALESCE(
                lesson_date::text,
                created_at::text,
                ''
            ) AS lesson_date,
    
    
            COALESCE(
                topic,
                'Homework Assignment'
            ) AS topic,
    
    
            COALESCE(
                percent,
                0
            ) AS percent,
    
    
            COALESCE(
                grade_letter,
                ''
            ) AS grade_letter,
    
    
            COALESCE(
                teacher_comment,
                ''
            ) AS teacher_comment
    
    
        FROM homework_grades
    
    
        WHERE student_id = %s
    
    
        ORDER BY lesson_date ASC
    
        """,
        (
            student_id,
        )
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



    chart_data = grades.dropna(
        subset=["lesson_date"]
    ).copy()


    if chart_data.empty:

        st.info(
            "No valid dates available for chart."
        )

        return


    chart_data["formatted_date"] = (
        chart_data["lesson_date"]
        .dt.strftime("%Y-%m-%d")
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
                    title="Lesson Date"
                ),

                y=alt.Y(
                    "percent:Q",
                    title="Score (%)",
                    scale=alt.Scale(
                        domain=[0,100]
                    )
                ),

                tooltip=[
                    alt.Tooltip(
                        "formatted_date:N",
                        title="Date"
                    ),
                
                    alt.Tooltip(
                        "topic:N",
                        title="Topic"
                    ),
                
                    alt.Tooltip(
                        "percent:Q",
                        title="Score (%)"
                    ),
                
                    alt.Tooltip(
                        "grade_letter:N",
                        title="Grade"
                    ),
                
                    alt.Tooltip(
                        "record_status:N",
                        title="Record"
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

        fallback = chart_data[
            [
                "lesson_date",
                "percent"
            ]
        ].set_index(
            "lesson_date"
        )

        st.line_chart(
            fallback
        )
