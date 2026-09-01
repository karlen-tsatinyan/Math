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


# GRADE QUERY
# ============================================================

def get_student_grades(student_id, selected_course):
    """
    Load graded homework for a student.

    Rules:
    - Must belong to the selected student
    - Must have a grade
    - Must have a due date
    - Course matching is flexible
    - If course names do not match exactly, we still use the
      student's graded homework rather than hiding the grades
    """

    grades = query_dataframe(
        """
        SELECT
            id,
            due_date::text AS lesson_date,
            course,
            COALESCE(
                curriculum_topic,
                title,
                'Homework Assignment'
            ) AS topic,
            title AS homework_title,
            grade AS grade_letter,
            COALESCE(
                teacher_feedback,
                ''
            ) AS teacher_comment
        FROM homework
        WHERE student_id = %s
          AND due_date IS NOT NULL
          AND grade IS NOT NULL
          AND TRIM(grade) <> ''
        ORDER BY due_date ASC, id ASC
        """,
        (student_id,)
    )

    if grades.empty:
        return grades

    grades = grades.copy()

    # --------------------------------------------------------
    # NORMALIZE COURSE NAME
    # --------------------------------------------------------

    def normalize_course(value):

        if value is None:
            return ""

        text = str(value).strip().lower()

        if text in ["", "nan", "none", "null"]:
            return ""

        # Normalize spacing and punctuation
        text = (
            text
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )

        # Roman numerals
        replacements = {
            "iii": "3",
            "ii": "2",
            "iv": "4",
            "i": "1"
        }

        for roman, number in replacements.items():

            if text.endswith(roman):

                prefix = text[:-len(roman)]

                if prefix:
                    text = prefix + number
                    break

        return text

    selected_normalized = normalize_course(
        selected_course
    )

    grades["_normalized_course"] = (
        grades["course"]
        .apply(normalize_course)
    )

    # --------------------------------------------------------
    # COURSE MATCH
    # --------------------------------------------------------

    matched = grades[
        grades["_normalized_course"]
        == selected_normalized
    ].copy()

    # --------------------------------------------------------
    # IMPORTANT FALLBACK
    #
    # If course names don't match because of legacy homework
    # records, don't hide the grades.
    # The Admin already selected this student's course.
    # --------------------------------------------------------

    if not matched.empty:

        grades = matched

    else:

        # Use all graded homework for this student.
        grades = grades.copy()

    # --------------------------------------------------------
    # REMOVE INTERNAL COLUMN
    # --------------------------------------------------------

    grades.drop(
        columns=["_normalized_course"],
        inplace=True,
        errors="ignore"
    )

    # --------------------------------------------------------
    # CONVERT LETTER GRADE → PERCENT
    # --------------------------------------------------------

    grades["percent"] = (
        grades["grade_letter"]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(GRADE_MAP)
    )

    # --------------------------------------------------------
    # REMOVE UNKNOWN GRADES
    # --------------------------------------------------------

    grades = grades[
        grades["percent"].notna()
    ].copy()

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    grades = grades.sort_values(
        by=["lesson_date", "id"],
        ascending=True
    ).reset_index(drop=True)

    return grades


# ============================================================
# CLEAN GRADES
# ============================================================

def clean_grade_data(grades):

    if grades.empty:
        return grades

    grades = grades.copy()

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    grades["lesson_date"] = pd.to_datetime(
        grades["lesson_date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # PERCENTAGE
    # --------------------------------------------------------

    grades["percent"] = pd.to_numeric(
        grades["percent"],
        errors="coerce"
    )

    grades = grades[
        grades["percent"].notna()
    ].copy()

    # --------------------------------------------------------
    # SORT BY DUE DATE
    # --------------------------------------------------------

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

            "course":
                "Course",

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
        "Course",
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
    
        st.warning(
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
# STUDENT PERFORMANCE VIEW USED BY:
#
#   1. Student Portal
#   2. Admin → Student Profile


# ============================================================
# STUDENT PERFORMANCE VIEW
# Used by Student Portal AND Admin Student Profile
# ============================================================

def student_performance_view(student_id):

    st.subheader(
        "📈 Advanced Progression Analytics"
    )

    # ========================================================
    # DETERMINE COURSE
    #
    # Priority:
    #
    # 1. Student Portal selected_course
    # 2. Admin Student Profile selected student's subject
    #
    # This is important because the Admin Student Profile
    # does NOT necessarily have:
    #
    # st.session_state.user["selected_course"]
    #
    # ========================================================

    selected_course = None

    # --------------------------------------------------------
    # 1. TRY USER SESSION
    # --------------------------------------------------------

    user = st.session_state.get(
        "user",
        {}
    )

    if isinstance(user, dict):

        selected_course = user.get(
            "selected_course"
        )

    # --------------------------------------------------------
    # 2. TRY GENERAL SESSION STATE
    # --------------------------------------------------------

    if not selected_course:

        selected_course = st.session_state.get(
            "selected_course"
        )

    # --------------------------------------------------------
    # 3. ADMIN STUDENT PROFILE FALLBACK
    #
    # Get the student's actual assigned course(s)
    # directly from the students table.
    # --------------------------------------------------------

    student_course_result = query_dataframe(
        """
        SELECT
            subject
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (student_id,)
    )

    courses = []

    if not student_course_result.empty:

        subject = student_course_result.iloc[0]["subject"]

        if (
            subject is not None
            and str(subject).strip()
            and str(subject).strip().lower()
            not in [
                "nan",
                "none",
                "null"
            ]
        ):

            courses = [
                course.strip()
                for course in str(subject).split(",")
                if course.strip()
            ]

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    courses = list(
        dict.fromkeys(courses)
    )

    # --------------------------------------------------------
    # VALIDATE EXISTING COURSE
    #
    # If the stored selected_course does not belong to this
    # student, do NOT use it.
    # --------------------------------------------------------

    if selected_course:

        selected_course = str(
            selected_course
        ).strip()

        matching_course = None

        for course in courses:

            if course.lower() == selected_course.lower():

                matching_course = course

                break

        if matching_course:

            selected_course = matching_course

        else:

            selected_course = None

    # --------------------------------------------------------
    # IF NO VALID COURSE WAS FOUND
    # --------------------------------------------------------

    if not selected_course:

        if len(courses) == 1:

            # Student has exactly ONE course.
            # Automatically use it.

            selected_course = courses[0]

        elif len(courses) > 1:

            # Student has multiple courses.
            # Allow the Admin/Student to select one.

            saved_course = st.session_state.get(
                "performance_selected_course"
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
                key=(
                    f"student_performance_course_"
                    f"{student_id}"
                )
            )

        else:

            st.warning(
                "This student does not have a course "
                "assigned in Student Management."
            )

            return

    # --------------------------------------------------------
    # SAVE COURSE FOR THIS PERFORMANCE VIEW
    # --------------------------------------------------------

    st.session_state[
        "performance_selected_course"
    ] = selected_course

    # Also make it available to other parts of the app.

    st.session_state[
        "selected_course"
    ] = selected_course

    # --------------------------------------------------------
    # COURSE HEADER
    # --------------------------------------------------------

    st.info(
        f"📚 Showing performance for **{selected_course}**"
    )

    # ========================================================
    # GET GRADED HOMEWORK
    # ========================================================
    # Match student + course.
    # Course comparison ignores accidental spaces/case.
    # Status comparison is also made more tolerant.
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
                WHEN UPPER(TRIM(grade)) = 'A+' THEN 98
                WHEN UPPER(TRIM(grade)) = 'A'  THEN 95
                WHEN UPPER(TRIM(grade)) = 'A-' THEN 92
                WHEN UPPER(TRIM(grade)) = 'B+' THEN 88
                WHEN UPPER(TRIM(grade)) = 'B'  THEN 85
                WHEN UPPER(TRIM(grade)) = 'B-' THEN 82
                WHEN UPPER(TRIM(grade)) = 'C+' THEN 78
                WHEN UPPER(TRIM(grade)) = 'C'  THEN 75
                WHEN UPPER(TRIM(grade)) = 'C-' THEN 72
                WHEN UPPER(TRIM(grade)) = 'D'  THEN 65
                WHEN UPPER(TRIM(grade)) = 'F'  THEN 50
                ELSE 0
            END AS percent,

            grade AS grade_letter,

            COALESCE(
                teacher_feedback,
                ''
            ) AS teacher_comment

        FROM homework

        WHERE student_id = %s

          AND LOWER(TRIM(course))
              = LOWER(TRIM(%s))

          AND LOWER(TRIM(status))
              IN (
                  'reviewed',
                  'graded',
                  'completed'
              )

          AND due_date IS NOT NULL

          AND grade IS NOT NULL

          AND TRIM(grade) <> ''

        ORDER BY
            due_date ASC,
            id ASC
        """,
        (
            student_id,
            selected_course
        )
    )

    # ========================================================
    # NO DATA
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
    ).reset_index(
        drop=True
    )

    # ========================================================
    # PERFORMANCE SUMMARY
    # ========================================================

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

    st.divider()

    # ========================================================
    # CHART DATA
    # ========================================================

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

    # ========================================================
    # CHART
    # ========================================================

    try:

        import altair as alt

        chart = (
            alt.Chart(
                chart_data
            )
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
            .set_index(
                "lesson_date"
            )
        )

        st.line_chart(
            fallback
        )

    # ========================================================
    # GRADE HISTORY
    # ========================================================

    st.divider()

    st.subheader(
        f"📋 {selected_course} Grade History"
    )

    history = grades.copy()

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
