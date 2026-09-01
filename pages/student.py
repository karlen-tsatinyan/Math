import streamlit as st
import pandas as pd

from utils.datetime_utils import today_str
from database import query_dataframe


# ============================================================
# CACHE SETTINGS
# ============================================================

CACHE_TTL = 300


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
    "F": 50,
}


# ============================================================
# HELPER — SAFE TEXT
# ============================================================

def safe_text(value):

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip()

    if text.lower() in [
        "",
        "nan",
        "none",
        "null",
    ]:
        return ""

    return text


# ============================================================
# HELPER — NORMALIZE COURSE NAME
# ============================================================

def normalize_course(value):

    text = safe_text(value).lower()

    if not text:
        return ""

    # Remove spaces and common punctuation
    text = (
        text
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace("/", "")
    )

    # Normalize common Roman numerals
    replacements = {
        "iii": "3",
        "ii": "2",
        "iv": "4",
        "i": "1",
    }

    for roman, number in replacements.items():

        if text.endswith(roman):

            prefix = text[:-len(roman)]

            if prefix:
                text = prefix + number
                break

    return text


# ============================================================
# STUDENT ID RESOLUTION
# ============================================================

def get_student_id():

    user = st.session_state.get(
        "user",
        {}
    )

    if not isinstance(user, dict):
        user = {}

    # --------------------------------------------------------
    # Preferred method
    # --------------------------------------------------------

    student_id = user.get(
        "student_id"
    )

    if student_id is not None:

        try:
            return int(student_id)

        except (
            ValueError,
            TypeError
        ):
            pass

    # --------------------------------------------------------
    # Fallback: user ID
    # --------------------------------------------------------

    user_id = user.get(
        "id"
    )

    if user_id:

        try:

            result = query_dataframe(
                """
                SELECT
                    student_id
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,)
            )

            if not result.empty:

                value = result.iloc[0][
                    "student_id"
                ]

                if value is not None:

                    try:
                        return int(value)

                    except (
                        ValueError,
                        TypeError
                    ):
                        pass

        except Exception:
            pass

    # --------------------------------------------------------
    # Final fallback: username
    # --------------------------------------------------------

    username = user.get(
        "username"
    )

    if username:

        try:

            result = query_dataframe(
                """
                SELECT
                    student_id
                FROM users
                WHERE LOWER(username) = LOWER(%s)
                LIMIT 1
                """,
                (username,)
            )

            if not result.empty:

                value = result.iloc[0][
                    "student_id"
                ]

                if value is not None:

                    try:
                        return int(value)

                    except (
                        ValueError,
                        TypeError
                    ):
                        pass

        except Exception:
            pass

    return None


# ============================================================
# STUDENT INFORMATION
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_student_info(student_id):

    if not student_id:
        return pd.DataFrame()

    try:

        return query_dataframe(
            """
            SELECT
                id,
                COALESCE(
                    first_name,
                    ''
                ) AS first_name,

                COALESCE(
                    last_name,
                    ''
                ) AS last_name,

                COALESCE(
                    grade,
                    'N/A'
                ) AS grade,

                COALESCE(
                    subject,
                    'N/A'
                ) AS subject,

                zoom_link,
                meeting_id

            FROM students

            WHERE id = %s

            LIMIT 1
            """,
            (int(student_id),)
        )

    except Exception as e:

        st.error(
            f"Unable to load student information: {e}"
        )

        return pd.DataFrame()


# ============================================================
# STUDENT COURSES
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_student_courses(student_id):

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

    subject_text = safe_text(
        subject
    )

    if not subject_text:
        return []

    courses = []

    for course in subject_text.split(","):

        course = safe_text(
            course
        )

        if not course:
            continue

        if not any(
            course.lower() == existing.lower()
            for existing in courses
        ):
            courses.append(course)

    return courses


# ============================================================
# DASHBOARD DATA
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_dashboard_data(
    student_id,
    today_date
):

    homework_due = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM homework
        WHERE student_id = %s
          AND COALESCE(
                archived,
                0
              ) = 0
          AND LOWER(
                TRIM(
                    COALESCE(status, '')
                )
              ) IN (
                'assigned',
                'submitted'
              )
        """,
        (student_id,)
    )

    sessions_count = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM sessions
        WHERE student_id = %s
          AND session_date >= %s
        """,
        (
            student_id,
            today_date
        )
    )

    payments_summary = query_dataframe(
        """
        SELECT
            COALESCE(
                SUM(amount),
                0
            ) AS total
        FROM payments
        WHERE student_id = %s
        """,
        (student_id,)
    )

    next_session = query_dataframe(
        """
        SELECT
            s.session_date,
            s.session_time,
            COALESCE(
                s.topic,
                ''
            ) AS topic,
            st.zoom_link,
            st.meeting_id

        FROM sessions s

        JOIN students st
            ON s.student_id = st.id

        WHERE s.student_id = %s
          AND s.session_date >= %s

        ORDER BY
            s.session_date ASC,
            s.session_time ASC

        LIMIT 1
        """,
        (
            student_id,
            today_date
        )
    )

    return {
        "homework_due": homework_due,
        "sessions_count": sessions_count,
        "payments_summary": payments_summary,
        "next_session": next_session,
    }


# ============================================================
# HOMEWORK GRADES
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_grades(student_id):

    return query_dataframe(
        """
        SELECT
            title AS "Homework",
            due_date AS "Due Date",
            grade AS "Grade",
            teacher_feedback AS "Teacher Feedback",
            reviewed_at AS "Graded On"

        FROM homework

        WHERE student_id = %s
          AND COALESCE(
                archived,
                0
              ) = 0

          AND grade IS NOT NULL

          AND TRIM(grade) <> ''

        ORDER BY
            due_date DESC
        """,
        (student_id,)
    )


# ============================================================
# SESSION HISTORY
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_session_history(student_id):

    return query_dataframe(
        """
        SELECT

            s.session_date AS "Date",

            s.session_time AS "Time",

            COALESCE(
                s.topic,
                ''
            ) AS "Topic",

            COALESCE(
                a.status,
                'Pending'
            ) AS "Attendance"

        FROM sessions s

        LEFT JOIN attendance a
            ON a.student_id =
                s.student_id

            AND a.session_date =
                s.session_date

            AND a.session_time =
                s.session_time

        WHERE
            s.student_id = %s

        ORDER BY

            s.session_date DESC,

            s.session_time DESC
        """,
        (student_id,)
    )


# ============================================================
# FINANCIAL DATA
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_payment_history(student_id):

    return query_dataframe(
        """
        SELECT
            amount,
            payment_date,
            period
        FROM payments
        WHERE student_id = %s
        ORDER BY
            payment_date DESC
        """,
        (student_id,)
    )


# ============================================================
# PARENT PIN
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_parent_pin(student_id):

    return query_dataframe(
        """
        SELECT
            parent_pin
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (student_id,)
    )


# ============================================================
# ADVANCED ANALYTICS — LOAD DATA
#
# IMPORTANT:
# This version intentionally does NOT require homework status
# to be Reviewed/Graded/Completed.
#
# If a homework item has a valid letter grade and due date,
# it is included in the student's progression.
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_advanced_performance_data(
    student_id,
    selected_course
):

    grades = query_dataframe(
        """
        SELECT

            id,

            due_date::text AS lesson_date,

            COALESCE(
                course,
                ''
            ) AS course,

            COALESCE(
                curriculum_topic,
                title,
                'Homework Assignment'
            ) AS topic,

            COALESCE(
                title,
                'Homework Assignment'
            ) AS homework_title,

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

          AND COALESCE(
                archived,
                0
              ) = 0

        ORDER BY
            due_date ASC,
            id ASC
        """,
        (student_id,)
    )

    if grades.empty:
        return grades

    grades = grades.copy()

    # --------------------------------------------------------
    # NORMALIZE COURSE
    # --------------------------------------------------------

    grades["_normalized_course"] = (
        grades["course"]
        .apply(normalize_course)
    )

    selected_normalized = normalize_course(
        selected_course
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
    # If no exact course match exists, use the student's
    # graded homework rather than displaying a blank chart.
    # --------------------------------------------------------

    if not matched.empty:

        grades = matched

    else:

        grades = grades.copy()

    # --------------------------------------------------------
    # LETTER → PERCENT
    # --------------------------------------------------------

    grades["grade_letter"] = (
        grades["grade_letter"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    grades["percent"] = (
        grades["grade_letter"]
        .map(GRADE_MAP)
    )

    # --------------------------------------------------------
    # REMOVE UNKNOWN GRADES
    # --------------------------------------------------------

    grades = grades[
        grades["percent"].notna()
    ].copy()

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    grades["lesson_date"] = pd.to_datetime(
        grades["lesson_date"],
        errors="coerce"
    )

    grades = grades[
        grades["lesson_date"].notna()
    ].copy()

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    grades = grades.sort_values(
        by=[
            "lesson_date",
            "id"
        ],
        ascending=True
    ).reset_index(
        drop=True
    )

    grades.drop(
        columns=[
            "_normalized_course"
        ],
        inplace=True,
        errors="ignore"
    )

    return grades


# ============================================================
# ADVANCED ANALYTICS — SUMMARY
# ============================================================

def display_advanced_summary(
    grades
):

    if grades.empty:
        return

    average = grades[
        "percent"
    ].mean()

    highest = grades[
        "percent"
    ].max()

    lowest = grades[
        "percent"
    ].min()

    if len(grades) > 1:

        improvement = (
            grades.iloc[-1]["percent"]
            -
            grades.iloc[0]["percent"]
        )

        trend = (
            f"{improvement:+.1f}%"
        )

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
# ADVANCED ANALYTICS — CHART
# ============================================================

def display_advanced_chart(
    grades,
    selected_course
):

    chart_data = grades.copy()

    chart_data = chart_data.dropna(
        subset=[
            "lesson_date"
        ]
    )

    if chart_data.empty:

        st.info(
            "No valid homework due dates are "
            "available for the progression chart."
        )

        return

    chart_data[
        "formatted_date"
    ] = (
        chart_data[
            "lesson_date"
        ]
        .dt.strftime(
            "%Y-%m-%d"
        )
    )

    st.caption(
        "Progression is plotted by homework due date, "
        "not by submission or grading date."
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
                title="Score (%)",
                scale=alt.Scale(
                    domain=[
                        0,
                        100
                    ]
                )
            )
        )

        points = base.mark_circle(
            size=90
        ).encode(

            y=alt.Y(
                "percent:Q",
                title="Score (%)",
                scale=alt.Scale(
                    domain=[
                        0,
                        100
                    ]
                )
            )
        )

        chart = (
            line
            +
            points
        ).interactive().properties(
            height=380,
            title=(
                f"{selected_course} "
                f"Homework Progression"
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
            .rename(
                columns={
                    "percent":
                        "Score (%)"
                }
            )
        )

        st.line_chart(
            fallback
        )


# ============================================================
# ADVANCED ANALYTICS — GRADE HISTORY
# ============================================================

def display_advanced_grade_history(
    grades,
    selected_course
):

    st.divider()

    st.subheader(
        f"📋 {selected_course} Grade History"
    )

    history = grades.copy()

    history["lesson_date"] = (
        history[
            "lesson_date"
        ]
        .dt.strftime(
            "%Y-%m-%d"
        )
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
                "Teacher Comments",
        }
    )

    history_columns = [

        "Due Date",

        "Course",

        "Homework",

        "Topic",

        "Percentage",

        "Grade",

        "Teacher Comments",

    ]

    history = history[
        [
            column
            for column
            in history_columns
            if column in history.columns
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
# ADVANCED PROGRESSION ANALYTICS
# ============================================================

def display_student_advanced_analytics(
    student_id,
    student
):

    # --------------------------------------------------------
    # GET COURSES
    # --------------------------------------------------------

    courses = get_student_courses(
        student_id
    )

    if not courses:

        st.warning(
            "This student does not have a course "
            "assigned in Student Management."
        )

        return

    # --------------------------------------------------------
    # DETERMINE CURRENT COURSE
    # --------------------------------------------------------

    user = st.session_state.get(
        "user",
        {}
    )

    selected_course = None

    if isinstance(
        user,
        dict
    ):

        selected_course = safe_text(
            user.get(
                "selected_course"
            )
        )

    if not selected_course:

        selected_course = safe_text(
            st.session_state.get(
                "selected_course"
            )
        )

    # --------------------------------------------------------
    # VALIDATE COURSE
    # --------------------------------------------------------

    valid_course = None

    if selected_course:

        for course in courses:

            if (
                normalize_course(course)
                ==
                normalize_course(
                    selected_course
                )
            ):

                valid_course = course
                break

    selected_course = valid_course

    # --------------------------------------------------------
    # MULTIPLE COURSES
    # --------------------------------------------------------

    if not selected_course:

        if len(courses) == 1:

            selected_course = courses[0]

        else:

            saved_course = (
                st.session_state.get(
                    "performance_selected_course"
                )
            )

            course_index = 0

            if saved_course:

                for i, course in enumerate(
                    courses
                ):

                    if (
                        normalize_course(course)
                        ==
                        normalize_course(
                            saved_course
                        )
                    ):

                        course_index = i
                        break

            selected_course = st.selectbox(

                "📚 Select Course",

                courses,

                index=course_index,

                key=(
                    "student_advanced_"
                    "performance_course"
                )
            )

    # --------------------------------------------------------
    # SAVE COURSE
    # --------------------------------------------------------

    st.session_state[
        "performance_selected_course"
    ] = selected_course

    st.session_state[
        "selected_course"
    ] = selected_course

    if isinstance(
        st.session_state.get("user"),
        dict
    ):

        st.session_state.user[
            "selected_course"
        ] = selected_course

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.info(
        f"📚 Showing performance for "
        f"**{selected_course}**"
    )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    grades = get_advanced_performance_data(
        student_id,
        selected_course
    )

    if grades.empty:

        st.info(
            f"No graded homework is available yet "
            f"for {selected_course}."
        )

        return

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    display_advanced_summary(
        grades
    )

    st.divider()

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    st.subheader(
        f"📈 {selected_course} Progression"
    )

    display_advanced_chart(
        grades,
        selected_course
    )

    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    display_advanced_grade_history(
        grades,
        selected_course
    )


# ============================================================
# STUDENT PAGE
# ============================================================

def student_page():

    # ========================================================
    # RESOLVE STUDENT
    # ========================================================

    student_id = get_student_id()

    if not student_id:

        st.error(
            "No linked student profile found for this user "
            "account. Please check with your administrator."
        )

        return

    # ========================================================
    # STUDENT INFORMATION
    # ========================================================

    student_df = get_student_info(
        student_id
    )

    if student_df.empty:

        st.error(
            f"No student record found for "
            f"Student ID: {student_id}"
        )

        return

    student = student_df.iloc[0]

    # ========================================================
    # SYNC STUDENT COURSE INFORMATION
    #
    # This is important for both:
    #   - Performance
    #   - My Homework
    #
    # The Homework module reads selected_course from
    # session state/user.
    # ========================================================

    courses = get_student_courses(
        student_id
    )

    user = st.session_state.get(
        "user",
        {}
    )

    if not isinstance(
        user,
        dict
    ):
        user = {}

    current_course = safe_text(
        user.get(
            "selected_course"
        )
    )

    if courses:

        matching_course = None

        if current_course:

            for course in courses:

                if (
                    normalize_course(course)
                    ==
                    normalize_course(
                        current_course
                    )
                ):

                    matching_course = course
                    break

        if matching_course:

            user[
                "selected_course"
            ] = matching_course

        elif len(courses) == 1:

            user[
                "selected_course"
            ] = courses[0]

        else:

            # Preserve existing selection if possible.
            if not current_course:
                user[
                    "selected_course"
                ] = courses[0]

    user[
        "student_id"
    ] = student_id

    user[
        "courses"
    ] = courses

    st.session_state[
        "user"
    ] = user

    # ========================================================
    # SIDEBAR CSS
    # ========================================================

    st.sidebar.markdown(
        """
        <style>

        .student-portal-title {

            font-size: 1.10rem;
            font-weight: 700;

            margin-top: -8px;
            margin-bottom: 7px;

            padding: 0;

            line-height: 1.1;
        }

        .student-section {

            font-size: 0.72rem;

            font-weight: 700;

            letter-spacing: 0.06em;

            margin-top: 9px;
            margin-bottom: 3px;

            padding-bottom: 3px;

            border-bottom:
                1px solid rgba(128,128,128,0.30);
        }

        .student-section.first {

            margin-top: 0px;
        }

        [data-testid="stSidebar"] .stButton {

            margin-bottom: 0px !important;
        }

        [data-testid="stSidebar"] .stButton > button {

            padding: 4px 8px !important;

            min-height: 30px !important;

            font-size: 0.86rem !important;

            text-align: left !important;

            justify-content: flex-start !important;

            border-radius: 5px !important;
        }

        [data-testid="stSidebar"] .element-container {

            margin-bottom: 0px !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # STUDENT PORTAL TITLE
    # ========================================================

    st.sidebar.markdown(
        """
        <div class="student-portal-title">
            📚 Student Portal
        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # MENU
    # ========================================================

    valid_student_options = [

        "🏠 Dashboard",

        "📚 Homework",

        "📊 Performance",

        "📅 Schedule",

        "💰 Financial Statements"

    ]

    if (
        "student_portal_menu"
        not in st.session_state
    ):

        st.session_state.student_portal_menu = (
            "🏠 Dashboard"
        )

    if (
        st.session_state.student_portal_menu
        not in valid_student_options
    ):

        st.session_state.student_portal_menu = (
            "🏠 Dashboard"
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def student_nav_button(
        label,
        value
    ):

        if st.sidebar.button(
            label,
            use_container_width=True,
            key=f"student_nav_{value}"
        ):

            st.session_state.student_portal_menu = (
                value
            )

            st.rerun()

    # ========================================================
    # MY LEARNING
    # ========================================================

    st.sidebar.markdown(
        '<div class="student-section first">'
        'MY LEARNING'
        '</div>',
        unsafe_allow_html=True
    )

    student_nav_button(
        "🏠 Dashboard",
        "🏠 Dashboard"
    )

    student_nav_button(
        "📚 Homework",
        "📚 Homework"
    )

    student_nav_button(
        "📊 Performance",
        "📊 Performance"
    )

    # ========================================================
    # SCHEDULE
    # ========================================================

    st.sidebar.markdown(
        '<div class="student-section">'
        'SCHEDULE'
        '</div>',
        unsafe_allow_html=True
    )

    student_nav_button(
        "📅 Schedule",
        "📅 Schedule"
    )

    # ========================================================
    # FINANCIAL
    # ========================================================

    st.sidebar.markdown(
        '<div class="student-section">'
        'FINANCIAL'
        '</div>',
        unsafe_allow_html=True
    )

    student_nav_button(
        "💰 Financial Statements",
        "💰 Financial Statements"
    )

    # ========================================================
    # CLASSROOM INFORMATION
    # ========================================================

    z_link = student.get(
        "zoom_link"
    )

    m_id = student.get(
        "meeting_id"
    )

    if z_link or m_id:

        st.sidebar.markdown(
            '<div class="student-section">'
            'CLASSROOM'
            '</div>',
            unsafe_allow_html=True
        )

        if (
            z_link
            and safe_text(z_link)
        ):

            st.sidebar.markdown(
                f"🔗 [General Zoom Room]({z_link})"
            )

        if (
            m_id
            and safe_text(m_id)
        ):

            st.sidebar.caption(
                f"Meeting ID: {m_id}"
            )

    # ========================================================
    # CURRENT PAGE
    # ========================================================

    option = st.session_state.get(
        "student_portal_menu",
        "🏠 Dashboard"
    )

    # ========================================================
    # DASHBOARD
    # ========================================================

    if option == "🏠 Dashboard":

        st.title(
            "Student Dashboard"
        )

        st.success(
            f"Welcome {student['first_name']} "
            f"{student['last_name']} "
            f"\u00a0\u00a0|\u00a0\u00a0 "
            f"Grade: {student['grade']} "
            f"\u00a0\u00a0|\u00a0\u00a0 "
            f"Courses: {student['subject']}"
        )

        dashboard = get_dashboard_data(
            student_id,
            today_str()
        )

        homework_due = dashboard[
            "homework_due"
        ]

        sessions_count = dashboard[
            "sessions_count"
        ]

        hw_total = (

            int(
                homework_due.iloc[0][
                    "total"
                ]
            )

            if not homework_due.empty

            else 0
        )

        sess_total = (

            int(
                sessions_count.iloc[0][
                    "total"
                ]
            )

            if not sessions_count.empty

            else 0
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "📚 Homework Due",
            hw_total
        )

        c2.metric(
            "📅 Upcoming Sessions",
            sess_total
        )

        st.divider()

        # ====================================================
        # NEXT SESSION
        # ====================================================

        st.subheader(
            "Next Upcoming Session"
        )

        next_session = dashboard[
            "next_session"
        ]

        if not next_session.empty:

            s = next_session.iloc[0]

            session_date = s[
                "session_date"
            ]

            session_time = s[
                "session_time"
            ]

            topic = s[
                "topic"
            ]

            st.info(
                f"**Date:** {session_date} "
                f"at {session_time} | "
                f"**Topic:** {topic}"
            )

            zoom_url = s.get(
                "zoom_link"
            )

            meeting_id = s.get(
                "meeting_id"
            )

            if (
                zoom_url
                and safe_text(zoom_url)
            ):

                st.markdown(
                    f"🔗 [Join Zoom Meeting]({zoom_url})"
                )

            elif (
                meeting_id
                and safe_text(meeting_id)
            ):

                st.caption(
                    f"Meeting ID: {meeting_id}"
                )

            else:

                st.caption(
                    "No Zoom information has been assigned "
                    "for this session yet."
                )

        else:

            st.write(
                "No upcoming sessions scheduled."
            )

    # ========================================================
    # HOMEWORK
    # ========================================================

    elif option == "📚 Homework":

        # ----------------------------------------------------
        # Keep the Homework module responsible for the full
        # homework/submission interface.
        #
        # We have already synchronized:
        #   user["student_id"]
        #   user["courses"]
        #   user["selected_course"]
        #
        # before reaching this point.
        # ----------------------------------------------------

        try:

            from modules.homework import (
                student_homework
            )

            student_homework()

        except Exception as e:

            st.error(
                "Unable to load My Homework."
            )

            with st.expander(
                "Technical details"
            ):

                st.write(
                    str(e)
                )

    # ========================================================
    # PERFORMANCE
    # ========================================================

    elif option == "📊 Performance":

        st.title(
            "📊 Performance"
        )

        performance_section = st.radio(
            "Performance Section",
            [
                "📚 Homework Grades",
                "📈 Advanced Progression Analytics",
                "📅 Session History"
            ],
            horizontal=True,
            key="student_performance_section"
        )

        # ====================================================
        # HOMEWORK GRADES
        # ====================================================

        if (
            performance_section
            == "📚 Homework Grades"
        ):

            st.subheader(
                "Homework Grades"
            )

            grades = get_grades(
                student_id
            )

            if grades.empty:

                st.info(
                    "No graded homework available yet."
                )

            else:

                st.dataframe(
                    grades,
                    use_container_width=True,
                    hide_index=True
                )

        # ====================================================
        # ADVANCED ANALYTICS
        # ====================================================

        elif (
            performance_section
            == "📈 Advanced Progression Analytics"
        ):

            display_student_advanced_analytics(
                student_id,
                student
            )

        # ====================================================
        # SESSION HISTORY
        # ====================================================

        elif (
            performance_section
            == "📅 Session History"
        ):

            st.subheader(
                "Session History"
            )

            sessions_history = (
                get_session_history(
                    student_id
                )
            )

            if sessions_history.empty:

                st.info(
                    "No session history available."
                )

            else:

                for (
                    index,
                    row
                ) in sessions_history.iterrows():

                    session_date = row[
                        "Date"
                    ]

                    session_time = row[
                        "Time"
                    ]

                    topic = row[
                        "Topic"
                    ]

                    attendance = row[
                        "Attendance"
                    ]

                    col1, col2, col3, col4 = (
                        st.columns(
                            [
                                1.2,
                                1.1,
                                3,
                                1.3
                            ]
                        )
                    )

                    with col1:

                        st.write(
                            f"📅 {session_date}"
                        )

                    with col2:

                        st.write(
                            f"⏰ {session_time}"
                        )

                    with col3:

                        st.write(
                            f"📘 {topic}"
                        )

                        if attendance == "Present":

                            st.success(
                                "Attendance: Present"
                            )

                        elif attendance == "Late":

                            st.warning(
                                "Attendance: Late"
                            )

                        elif (
                            attendance
                            == "Absent - Excused"
                        ):

                            st.warning(
                                "Attendance: "
                                "Excused Absence"
                            )

                        elif (
                            attendance
                            == "Absent - Unexcused"
                        ):

                            st.error(
                                "Attendance: "
                                "Unexcused Absence"
                            )

                        else:

                            st.caption(
                                "Attendance: Pending"
                            )

                    with col4:

                        if st.button(
                            "📖 Review Topic",
                            key=(
                                f"review_session_topic_"
                                f"{student_id}_{index}"
                            )
                        ):

                            with st.spinner(
                                "🤖 Creating your "
                                "topic reference..."
                            ):

                                from (
                                    modules
                                    .ai_learning_reference
                                    import
                                    generate_learning_reference
                                )

                                result = (
                                    generate_learning_reference(

                                        curriculum_topic=str(
                                            topic
                                        ),

                                        homework_title="",

                                        instructions="",

                                        student_grade=str(
                                            student["grade"]
                                        )
                                    )
                                )

                            if result.get(
                                "success"
                            ):

                                st.session_state[
                                    f"session_learning_"
                                    f"{student_id}_{index}"
                                ] = result

                            else:

                                st.error(
                                    result.get(
                                        "error",
                                        "Unable to create "
                                        "topic reference."
                                    )
                                )

                    # ----------------------------------------
                    # AI TOPIC REFERENCE
                    # ----------------------------------------

                    session_learning = (
                        st.session_state.get(
                            f"session_learning_"
                            f"{student_id}_{index}"
                        )
                    )

                    if session_learning:

                        from (
                            modules
                            .ai_learning_reference
                            import
                            display_learning_reference
                        )

                        with st.container(
                            border=True
                        ):

                            display_learning_reference(
                                session_learning
                            )

                    st.divider()

    # ========================================================
    # FINANCIAL STATEMENTS
    # ========================================================

    elif option == "💰 Financial Statements":

        st.session_state.student_portal_menu = (
            "💰 Financial Statements"
        )

        from modules.student_financials import (
            student_financials
        )

        student_financials()

    # ========================================================
    # SCHEDULE
    # ========================================================

    elif option == "📅 Schedule":

        st.title(
            "📅 My Schedule"
        )

        st.caption(
            "View your tutoring sessions and attendance."
        )

        sessions = get_session_history(
            student_id
        )

        if sessions.empty:

            st.info(
                "No sessions found."
            )

        else:

            # ------------------------------------------------
            # NORMALIZE DATES
            # ------------------------------------------------

            sessions["Date"] = pd.to_datetime(
                sessions["Date"],
                errors="coerce"
            )

            sessions = sessions.dropna(
                subset=[
                    "Date"
                ]
            )

            today = pd.to_datetime(
                today_str()
            )

            # ------------------------------------------------
            # FILTER
            # ------------------------------------------------

            filter_option = st.selectbox(
                "Show Sessions",
                [
                    "Upcoming Sessions",
                    "Recent 5 + Upcoming 3",
                    "Last 10 Sessions",
                    "Last 30 Days",
                    "All Sessions"
                ],
                key="student_session_filter"
            )

            # ------------------------------------------------
            # UPCOMING
            # ------------------------------------------------

            if (
                filter_option
                == "Upcoming Sessions"
            ):

                sessions_display = (

                    sessions[
                        sessions["Date"] >= today
                    ]

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ]
                    )
                )

            # ------------------------------------------------
            # RECENT + UPCOMING
            # ------------------------------------------------

            elif (
                filter_option
                == "Recent 5 + Upcoming 3"
            ):

                recent = (

                    sessions[
                        sessions["Date"] < today
                    ]

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ],
                        ascending=False
                    )

                    .head(5)
                )

                upcoming = (

                    sessions[
                        sessions["Date"] >= today
                    ]

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ]
                    )

                    .head(3)
                )

                sessions_display = pd.concat(
                    [
                        upcoming,
                        recent
                    ],
                    ignore_index=True
                )

            # ------------------------------------------------
            # LAST 10
            # ------------------------------------------------

            elif (
                filter_option
                == "Last 10 Sessions"
            ):

                sessions_display = (

                    sessions

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ],
                        ascending=False
                    )

                    .head(10)
                )

            # ------------------------------------------------
            # LAST 30 DAYS
            # ------------------------------------------------

            elif (
                filter_option
                == "Last 30 Days"
            ):

                start_date = (
                    today
                    -
                    pd.Timedelta(
                        days=30
                    )
                )

                sessions_display = (

                    sessions[
                        sessions["Date"]
                        >= start_date
                    ]

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ],
                        ascending=False
                    )
                )

            # ------------------------------------------------
            # ALL
            # ------------------------------------------------

            else:

                sessions_display = (

                    sessions

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ],
                        ascending=False
                    )
                )

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            if sessions_display.empty:

                st.info(
                    "No sessions match the selected filter."
                )

            else:

                display_sessions = (
                    sessions_display.copy()
                )

                display_sessions["Date"] = (

                    pd.to_datetime(
                        display_sessions["Date"],
                        errors="coerce"
                    )

                    .dt.strftime(
                        "%Y-%m-%d"
                    )
                )

                st.dataframe(

                    display_sessions[
                        [
                            "Date",
                            "Time",
                            "Topic",
                            "Attendance"
                        ]
                    ],

                    use_container_width=True,

                    hide_index=True,

                    column_config={

                        "Date":
                            st.column_config.TextColumn(
                                "📅 Date"
                            ),

                        "Time":
                            st.column_config.TextColumn(
                                "⏰ Time"
                            ),

                        "Topic":
                            st.column_config.TextColumn(
                                "📘 Topic"
                            ),

                        "Attendance":
                            st.column_config.TextColumn(
                                "✅ Attendance"
                            )
                    }
                )

                # ------------------------------------------------
                # UPCOMING SESSION DETAILS
                # ------------------------------------------------

                upcoming_sessions = (

                    sessions[
                        sessions["Date"] >= today
                    ]

                    .sort_values(
                        [
                            "Date",
                            "Time"
                        ]
                    )
                )

                if not upcoming_sessions.empty:

                    st.divider()

                    st.subheader(
                        "📌 Next Sessions"
                    )

                    for (
                        index,
                        row
                    ) in (
                        upcoming_sessions
                        .head(3)
                        .iterrows()
                    ):

                        session_date = row[
                            "Date"
                        ]

                        session_time = row[
                            "Time"
                        ]

                        topic = row[
                            "Topic"
                        ]

                        attendance = row[
                            "Attendance"
                        ]

                        with st.container(
                            border=True
                        ):

                            c1, c2, c3 = (
                                st.columns(
                                    [
                                        1.5,
                                        1.5,
                                        4
                                    ]
                                )
                            )

                            with c1:

                                st.write(
                                    "📅 "
                                    +
                                    session_date.strftime(
                                        "%A, %b %d, %Y"
                                    )
                                )

                            with c2:

                                st.write(
                                    "⏰ "
                                    +
                                    str(
                                        session_time
                                    )
                                )

                            with c3:

                                st.write(
                                    "📘 "
                                    +
                                    (
                                        str(topic)
                                        if topic
                                        else
                                        "Tutoring Session"
                                    )
                                )

                                if (
                                    attendance
                                    and attendance
                                    != "Pending"
                                ):

                                    st.caption(
                                        f"Attendance: "
                                        f"{attendance}"
                                    )

                                else:

                                    st.caption(
                                        "Attendance: Pending"
                                    )

                    # ------------------------------------------------
                    # ZOOM
                    # ------------------------------------------------

                    zoom_result = query_dataframe(
                        """
                        SELECT
                            zoom_link,
                            meeting_id
                        FROM students
                        WHERE id = %s
                        LIMIT 1
                        """,
                        (student_id,)
                    )

                    if not zoom_result.empty:

                        zoom_link = (
                            zoom_result.iloc[0][
                                "zoom_link"
                            ]
                        )

                        meeting_id = (
                            zoom_result.iloc[0][
                                "meeting_id"
                            ]
                        )

                        if (
                            zoom_link
                            and safe_text(
                                zoom_link
                            )
                        ):

                            st.markdown(
                                f"🔗 "
                                f"[Join Zoom Classroom]"
                                f"({zoom_link})"
                            )

                        elif (
                            meeting_id
                            and safe_text(
                                meeting_id
                            )
                        ):

                            st.info(
                                f"Zoom Meeting ID: "
                                f"{meeting_id}"
                            )
