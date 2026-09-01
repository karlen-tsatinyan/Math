import streamlit as st
import pandas as pd

from database import query_dataframe


# ============================================================
# GRADE MAP
# ============================================================

GRADE_MAP = {
    "A+": 98,
    "A": 95,
    "A-": 92,
    "B+": 88,
    "B": 85,
    "B-": 82,
    "C+": 78,
    "C": 75,
    "C-": 72,
    "D": 65,
    "F": 50
}


# ============================================================
# COURSE HELPERS
# ============================================================

def get_student_courses(student_id):
    """
    Return the courses assigned to a student.

    The students.subject field may contain:
        Algebra

    or:
        Algebra, Geometry
    """

    result = query_dataframe(
        """
        SELECT
            subject
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (student_id,)
    )

    if result.empty:
        return []

    subject = result.iloc[0]["subject"]

    if subject is None:
        return []

    subject_text = str(subject).strip()

    if not subject_text:
        return []

    if subject_text.lower() in [
        "nan",
        "none",
        "null"
    ]:
        return []

    courses = []

    for course in subject_text.split(","):

        course = course.strip()

        if not course:
            continue

        if course.lower() in [
            "nan",
            "none",
            "null"
        ]:
            continue

        if not any(
            course.lower() == existing.lower()
            for existing in courses
        ):
            courses.append(course)

    return courses


# ============================================================
# GRADE QUERY
# ============================================================

def get_student_grades(
    student_id,
    selected_course
):
    """
    Load reviewed homework grades for one student/course.

    Progression uses homework due_date.
    """

    return query_dataframe(
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
          AND course = %s
          AND status = 'Reviewed'
          AND due_date IS NOT NULL

        ORDER BY
            due_date ASC,
            id ASC
        """,
        (
            student_id,
            selected_course
        )
    )


# ============================================================
# CLEAN GRADES
# ============================================================

def clean_grade_data(grades):

    if grades.empty:
        return grades

    grades = grades.copy()

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

    return grades


# ============================================================
# PERFORMANCE CHART
# ============================================================

def display_progression_chart(
    grades,
    title="Homework Progression"
):

    chart_data = grades.dropna(
        subset=["lesson_date"]
    ).copy()

    if chart_data.empty:

        st.info(
            "No valid due dates available to render "
            "the progression chart."
        )

        return

    chart_data["formatted_date"] = (
        chart_data["lesson_date"]
        .dt.strftime("%Y-%m-%d")
    )

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
            title=title,
            height=380
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
            .set_index(
                "lesson_date"
            )
        )

        fallback.rename(
            columns={
                "percent": "Score (%)"
            },
            inplace=True
        )

        st.line_chart(
            fallback
        )


# ============================================================
# PERFORMANCE SUMMARY
# ============================================================

def display_performance_summary(grades):

    average = grades["percent"].mean()
    highest = grades["percent"].max()
    lowest = grades["percent"].min()

    if len(grades) > 1:

        improvement = (
            grades.iloc[-1]["percent"]
            - grades.iloc[0]["percent"]
        )

        trend = f"{improvement:+.1f}%"

    else:

        trend = "Baseline"

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
        trend
    )


# ============================================================
# GRADE HISTORY
# ============================================================

def display_grade_history(
    grades,
    selected_course
):

    st.divider()

    st.subheader(
        f"📋 {selected_course} Grade History"
    )

    history = grades.copy()

    if pd.api.types.is_datetime64_any_dtype(
        history["lesson_date"]
    ):

        history["lesson_date"] = (
            history["lesson_date"]
            .dt.strftime("%Y-%m-%d")
        )

    history = history.rename(
        columns={

            "lesson_date":
                "Due Date",

            "homework_title":
                "Homework",

            "topic":
                "Topic",

            "percent":
                "Percentage",

            "grade_letter":
                "Grade",

            "teacher_comment":
                "Teacher Comments"
        }
    )

    history_columns = [
        "Due Date",
        "Homework",
        "Topic",
        "Percentage",
        "Grade",
        "Teacher Comments"
    ]

    history = history[
        [
            col
            for col in history_columns
            if col in history.columns
        ]
    ]

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True,
        column_config={

            "Percentage":
                st.column_config.NumberColumn(
                    "Percentage",
                    format="%.1f%%"
                )
        }
    )


# ============================================================
# PERFORMANCE PROGRESSION DASHBOARD
# ADMIN / STANDALONE PERFORMANCE PAGE
# ============================================================

def performance_dashboard():

    st.title(
        "📈 Performance Progression Tracking"
    )

    # --------------------------------------------------------
    # STUDENT SELECTION
    # --------------------------------------------------------

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
            "No students available. "
            "Please enroll students first."
        )

        return

    student_options = {
        f"{row['name']} (ID: {row['id']})":
            row["id"]
        for _, row in students.iterrows()
    }

    saved_student_id = (
        st.session_state.get(
            "selected_student_id"
        )
    )

    default_index = 0

    if saved_student_id:

        for idx, (_, s_id) in enumerate(
            student_options.items()
        ):

            if s_id == saved_student_id:

                default_index = idx
                break

    selected_label = st.selectbox(
        "Select Student",
        options=list(
            student_options.keys()
        ),
        index=default_index,
        key="performance_student_select"
    )

    student_id = student_options[
        selected_label
    ]

    st.session_state.selected_student_id = (
        student_id
    )

    # --------------------------------------------------------
    # GET COURSES
    # --------------------------------------------------------

    courses = get_student_courses(
        student_id
    )

    if not courses:

        st.info(
            "No courses are assigned to this student."
        )

        return

    # --------------------------------------------------------
    # COURSE SELECTION
    # --------------------------------------------------------

    saved_course = (
        st.session_state.get(
            "performance_selected_course"
        )
    )

    course_index = 0

    if saved_course in courses:

        course_index = courses.index(
            saved_course
        )

    selected_course = st.selectbox(
        "Select Course",
        courses,
        index=course_index,
        key="performance_course_select"
    )

    st.session_state[
        "performance_selected_course"
    ] = selected_course

    # --------------------------------------------------------
    # DISPLAY PERFORMANCE
    # --------------------------------------------------------

    st.info(
        f"📚 Showing performance for "
        f"**{selected_course}**"
    )

    grades = get_student_grades(
        student_id,
        selected_course
    )

    if grades.empty:

        st.info(
            f"No graded homework with due dates "
            f"was found for {selected_course}."
        )

        return

    grades = clean_grade_data(
        grades
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab1, tab2 = st.tabs(
        [
            "Dashboard",
            "Grade History"
        ]
    )

    # ========================================================
    # TAB 1 — DASHBOARD
    # ========================================================

    with tab1:

        display_performance_summary(
            grades
        )

        st.divider()

        st.subheader(
            f"📊 {selected_course} Progression"
        )

        st.caption(
            "Progression is plotted by homework due date, "
            "not by the date the homework was submitted "
            "or graded."
        )

        display_progression_chart(
            grades,
            title=f"{selected_course} Progression"
        )

    # ========================================================
    # TAB 2 — GRADE HISTORY
    # ========================================================

    with tab2:

        display_grade_history(
            grades,
            selected_course
        )


# ============================================================
# STUDENT PERFORMANCE VIEW
#
# USED BY:
#
#   1. Student Portal
#   2. Admin → Student Profile
#
# ============================================================

def student_performance_view(student_id):

    st.subheader(
        "📈 Student Performance"
    )

    # ========================================================
    # DETERMINE STUDENT COURSES
    # ========================================================

    courses = get_student_courses(
        student_id
    )

    # --------------------------------------------------------
    # NO COURSE
    # --------------------------------------------------------

    if not courses:

        st.warning(
            "No courses are assigned to this student."
        )

        return

    # ========================================================
    # DETERMINE WHETHER THIS IS ADMIN OR STUDENT VIEW
    # ========================================================

    user = st.session_state.get(
        "user",
        {}
    )

    user_role = str(
        user.get(
            "role",
            ""
        )
    ).lower().strip()

    is_admin_view = (
        user_role in [
            "admin",
            "teacher",
            "administrator"
        ]
    )

    # ========================================================
    # COURSE SELECTION
    # ========================================================

    selected_course = None

    # --------------------------------------------------------
    # ADMIN STUDENT PROFILE
    #
    # If the student has one course:
    # automatically use it.
    #
    # If multiple courses:
    # let admin select one.
    # --------------------------------------------------------

    if is_admin_view:

        if len(courses) == 1:

            selected_course = courses[0]

            st.info(
                f"📚 Course: **{selected_course}**"
            )

        else:

            profile_course_key = (
                f"student_profile_performance_course_"
                f"{student_id}"
            )

            saved_course = (
                st.session_state.get(
                    profile_course_key
                )
            )

            course_index = 0

            if saved_course in courses:

                course_index = courses.index(
                    saved_course
                )

            selected_course = st.selectbox(
                "Select Course",
                courses,
                index=course_index,
                key=profile_course_key
            )

            st.session_state[
                profile_course_key
            ] = selected_course

    # --------------------------------------------------------
    # STUDENT PORTAL
    #
    # Continue using the student's selected course.
    # --------------------------------------------------------

    else:

        user_course = user.get(
            "selected_course"
        )

        if not user_course:

            user_course = (
                st.session_state.get(
                    "selected_course"
                )
            )

        # ----------------------------------------------------
        # If there is only one course, automatically use it.
        # This also makes the portal more robust.
        # ----------------------------------------------------

        if not user_course and len(courses) == 1:

            user_course = courses[0]

        # ----------------------------------------------------
        # Validate selected course
        # ----------------------------------------------------

        if user_course in courses:

            selected_course = user_course

        # ----------------------------------------------------
        # Selected course no longer exists
        # ----------------------------------------------------

        elif user_course:

            matching_course = next(
                (
                    course
                    for course in courses
                    if course.lower()
                    == str(user_course).lower()
                ),
                None
            )

            if matching_course:

                selected_course = (
                    matching_course
                )

        # ----------------------------------------------------
        # Still no course
        # ----------------------------------------------------

        if not selected_course:

            if len(courses) == 1:

                selected_course = courses[0]

            else:

                st.warning(
                    "Please select a course before "
                    "viewing performance."
                )

                return

    # ========================================================
    # COURSE HEADER
    # ========================================================

    st.info(
        f"📚 Showing performance for "
        f"**{selected_course}**"
    )

    # ========================================================
    # LOAD GRADED HOMEWORK
    # ========================================================

    grades = get_student_grades(
        student_id,
        selected_course
    )

    # ========================================================
    # NO PERFORMANCE DATA
    # ========================================================

    if grades.empty:

        st.info(
            f"No performance data available yet "
            f"for {selected_course}."
        )

        return

    # ========================================================
    # CLEAN DATA
    # ========================================================

    grades = clean_grade_data(
        grades
    )

    # ========================================================
    # PERFORMANCE SUMMARY
    # ========================================================

    display_performance_summary(
        grades
    )

    st.divider()

    # ========================================================
    # PROGRESSION CHART
    # ========================================================

    st.subheader(
        f"📊 {selected_course} Progression"
    )

    st.caption(
        "Progression is plotted by homework due date, "
        "not by submission or grading date."
    )

    display_progression_chart(
        grades,
        title=f"{selected_course} Progression"
    )

    # ========================================================
    # GRADE HISTORY
    # ========================================================

    display_grade_history(
        grades,
        selected_course
    )
