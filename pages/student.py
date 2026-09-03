import streamlit as st
import pandas as pd

from utils.datetime_utils import today_str
from database import query_dataframe


# ============================================================
# CACHE SETTINGS
# ============================================================

CACHE_TTL = 300


# ============================================================
# STUDENT ID RESOLUTION
# ============================================================

def get_student_id():

    user = st.session_state.get("user", {})

    if not isinstance(user, dict):
        return None

    # --------------------------------------------------------
    # Preferred method
    # --------------------------------------------------------

    student_id = user.get("student_id")

    if student_id is not None:

        try:
            return int(student_id)

        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # Fallback: user ID
    # --------------------------------------------------------

    user_id = user.get("id")

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

                value = result.iloc[0]["student_id"]

                if value is not None:

                    try:
                        return int(value)

                    except (ValueError, TypeError):
                        pass

        except Exception:
            pass

    # --------------------------------------------------------
    # Final fallback: username
    # --------------------------------------------------------

    username = user.get("username")

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

                value = result.iloc[0]["student_id"]

                if value is not None:

                    try:
                        return int(value)

                    except (ValueError, TypeError):
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

    # --------------------------------------------------------
    # HOMEWORK DUE
    #
    # COALESCE is intentional so NULL archived values
    # are treated as active homework.
    # --------------------------------------------------------

    homework_due = query_dataframe(
        """
        SELECT
            COUNT(*) AS total

        FROM homework

        WHERE student_id = %s

          AND status = 'Assigned'

          AND COALESCE(
              archived,
              0
          ) = 0
        """,
        (student_id,)
    )

    # --------------------------------------------------------
    # UPCOMING SESSIONS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # NEXT SESSION
    # --------------------------------------------------------

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
        "next_session": next_session
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

          AND TRIM(
              grade
          ) <> ''

        ORDER BY
            due_date DESC
        """,
        (student_id,)
    )


# ============================================================
# STUDENT PROGRESSION DATA
#
# This intentionally uses the same grade mapping used by
# the working Performance module.
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_progression_grades(student_id):

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

                WHEN grade = 'A' THEN 95

                WHEN grade = 'A-' THEN 92

                WHEN grade = 'B+' THEN 88

                WHEN grade = 'B' THEN 85

                WHEN grade = 'B-' THEN 82

                WHEN grade = 'C+' THEN 78

                WHEN grade = 'C' THEN 75

                WHEN grade = 'C-' THEN 72

                WHEN grade = 'D' THEN 65

                WHEN grade = 'F' THEN 50

                ELSE NULL

            END AS percent,

            grade AS grade_letter,

            COALESCE(
                teacher_feedback,
                ''
            ) AS teacher_comment

        FROM homework

        WHERE student_id = %s

          AND COALESCE(
              archived,
              0
          ) = 0

          AND grade IS NOT NULL

          AND TRIM(
              grade
          ) <> ''

          AND due_date IS NOT NULL

        ORDER BY
            due_date ASC,
            id ASC
        """,
        (student_id,)
    )

    if grades.empty:
        return grades

    grades["lesson_date"] = pd.to_datetime(
        grades["lesson_date"],
        errors="coerce"
    )

    grades["percent"] = pd.to_numeric(
        grades["percent"],
        errors="coerce"
    )

    grades = grades.dropna(
        subset=[
            "lesson_date",
            "percent"
        ]
    )

    grades = grades.sort_values(
        by=[
            "lesson_date"
        ],
        ascending=True
    ).reset_index(
        drop=True
    )

    return grades


# ============================================================
# ADVANCED PROGRESSION ANALYTICS
# ============================================================

def display_student_progression(
    student_id
):

    st.subheader(
        "📈 Advanced Progression Analytics"
    )

    grades = get_progression_grades(
        student_id
    )

    # --------------------------------------------------------
    # NO DATA
    # --------------------------------------------------------

    if grades.empty:

        st.info(
            "No graded homework with a valid due date "
            "is available yet."
        )

        return

    # --------------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------------

    average_score = grades[
        "percent"
    ].mean()

    highest_score = grades[
        "percent"
    ].max()

    lowest_score = grades[
        "percent"
    ].min()

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    if len(grades) >= 2:

        first_score = float(
            grades.iloc[0]["percent"]
        )

        last_score = float(
            grades.iloc[-1]["percent"]
        )

        difference = (
            last_score
            - first_score
        )

        if difference > 2:

            trend = "Improving ↑"

        elif difference < -2:

            trend = "Declining ↓"

        else:

            trend = "Stable →"

    else:

        trend = "Not enough data"

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Average",
            f"{average_score:.1f}%"
        )

    with c2:

        st.metric(
            "Highest",
            f"{highest_score:.1f}%"
        )

    with c3:

        st.metric(
            "Lowest",
            f"{lowest_score:.1f}%"
        )

    with c4:

        st.metric(
            "Trend",
            trend
        )

    st.divider()

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    st.markdown(
        "### 📈 Grade Progression"
    )

    st.caption(
        "Progression is plotted by homework due date, "
        "not by submission or grading date."
    )

    chart_data = grades.copy()

    chart_data[
        "formatted_date"
    ] = chart_data[
        "lesson_date"
    ].dt.strftime(
        "%Y-%m-%d"
    )

    try:

        import altair as alt

        base = alt.Chart(
            chart_data
        )

        line = base.mark_line(
            point=True
        ).encode(

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

        chart = (
            line
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
        ].copy()

        fallback = fallback.set_index(
            "lesson_date"
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

    # --------------------------------------------------------
    # GRADE HISTORY
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "### 📋 Grade History"
    )

    display_df = grades.copy()

    display_df[
        "lesson_date"
    ] = display_df[
        "lesson_date"
    ].dt.strftime(
        "%Y-%m-%d"
    )

    display_df = display_df.rename(
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
            column
            for column in columns_to_show
            if column in display_df.columns
        ]
    ]

    st.dataframe(

        display_df,

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
# SESSION HISTORY
#
# Attendance is matched by:
# student_id + session_date + session_time
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

        WHERE s.student_id = %s

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
# STUDENT PAGE
# ============================================================

def student_page():

    # ========================================================
    # RESOLVE STUDENT
    # ========================================================

    student_id = get_student_id()

    if not student_id:

        st.error(
            "No linked student profile found for this user account. "
            "Please check with your administrator."
        )

        return

    # ========================================================
    # IMPORTANT
    #
    # Keep the resolved student ID explicitly synchronized
    # with session_state so modules/homework.py always sees
    # the same student.
    # ========================================================

    user = st.session_state.get(
        "user",
        {}
    )

    if isinstance(user, dict):

        user["student_id"] = int(
            student_id
        )

        st.session_state.user = user

    st.session_state[
        "student_id"
    ] = int(student_id)

    # ========================================================
    # STUDENT INFORMATION
    # ========================================================

    student_df = get_student_info(
        student_id
    )

    if student_df.empty:

        st.error(
            f"No student record found for Student ID: "
            f"{student_id}"
        )

        return

    student = student_df.iloc[0]

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
            and str(z_link).strip()
            not in [
                "",
                "nan",
                "None"
            ]
        ):

            st.sidebar.markdown(
                f"🔗 [General Zoom Room]({z_link})"
            )

        if (
            m_id
            and str(m_id).strip()
            not in [
                "",
                "nan",
                "None"
            ]
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
                homework_due.iloc[0]["total"]
            )

            if not homework_due.empty

            else 0
        )

        sess_total = (

            int(
                sessions_count.iloc[0]["total"]
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
                and str(zoom_url).strip()
                not in [
                    "",
                    "nan",
                    "None"
                ]
            ):

                st.markdown(
                    f"🔗 [Join Zoom Meeting]({zoom_url})"
                )

            elif (
                meeting_id
                and str(meeting_id).strip()
                not in [
                    "",
                    "nan",
                    "None"
                ]
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

        st.title(
            "📚 My Homework"
        )

        st.caption(
            "Homework assigned to your student account."
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Keep the existing homework module because it
        # contains the complete assignment/submission system.
        # ----------------------------------------------------

        try:

            from modules.homework import (
                student_homework
            )

            student_homework()

        except Exception as e:

            st.error(
                "Unable to load your homework."
            )

            st.exception(e)

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

            display_student_progression(
                student_id
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
        
            sessions_history = get_session_history(
                student_id
            )
        
            if sessions_history.empty:
        
                st.info(
                    "No session history available."
                )
        
            else:
        
                # ------------------------------------------------
                # CLEAN / FORMAT DATE
                # ------------------------------------------------
        
                sessions_history = sessions_history.copy()
        
                # Keep the original date as a real datetime
                # so we can correctly separate upcoming/past.
                sessions_history["Date"] = pd.to_datetime(
                    sessions_history["Date"],
                    errors="coerce"
                )
        
                # If database returned Unix milliseconds,
                # try that format if normal conversion failed.
                if sessions_history["Date"].isna().all():
        
                    sessions_history["Date"] = pd.to_datetime(
                        sessions_history["Date"],
                        errors="coerce",
                        unit="ms"
                    )
        
                # ------------------------------------------------
                # SEPARATE UPCOMING / PAST
                # ------------------------------------------------
        
                today = pd.Timestamp.today().normalize()
        
                upcoming_sessions = sessions_history[
                    sessions_history["Date"] >= today
                ].sort_values(
                    "Date",
                    ascending=True
                )
        
                past_sessions = sessions_history[
                    sessions_history["Date"] < today
                ].sort_values(
                    "Date",
                    ascending=False
                )
        
                # ------------------------------------------------
                # SELECT FIRST 2 UPCOMING
                # ------------------------------------------------
        
                upcoming_display = upcoming_sessions.head(2)
        
                # ------------------------------------------------
                # SELECT 5 MOST RECENT PAST
                # ------------------------------------------------
        
                recent_past_display = past_sessions.head(5)
        
                # ------------------------------------------------
                # REMAINING PAST
                # ------------------------------------------------
        
                remaining_past = past_sessions.iloc[5:]
        
                # ------------------------------------------------
                # SCROLLABLE SESSION WINDOW
                # ------------------------------------------------
        
                with st.container(
                    height=650,
                    border=False
                ):
        
                    # =================================================
                    # UPCOMING SESSIONS
                    # =================================================
        
                    if not upcoming_display.empty:
        
                        st.markdown(
                            "### 📅 Upcoming Sessions"
                        )
        
                        for index, row in upcoming_display.iterrows():
        
                            # -----------------------------------------
                            # DATE
                            # -----------------------------------------
        
                            if pd.notna(row["Date"]):
        
                                session_date = (
                                    row["Date"]
                                    .strftime("%Y-%m-%d")
                                )
        
                            else:
        
                                session_date = "Unknown"
        
                            # -----------------------------------------
                            # TIME
                            # -----------------------------------------
        
                            session_time = str(
                                row["Time"]
                            ).strip()
        
                            # -----------------------------------------
                            # TOPIC
                            # -----------------------------------------
        
                            topic = str(
                                row["Topic"]
                            ).strip()
        
                            # -----------------------------------------
                            # ATTENDANCE
                            # -----------------------------------------
        
                            attendance = str(
                                row["Attendance"]
                            ).strip()
        
                            # -----------------------------------------
                            # COMPACT SESSION ROW
                            # -----------------------------------------
        
                            col1, col2, col3, col4 = st.columns(
                                [
                                    1.2,
                                    1.1,
                                    3.5,
                                    1.3
                                ]
                            )
        
                            with col1:
        
                                st.markdown(
                                    f"📅 {session_date}"
                                )
        
                            with col2:
        
                                st.markdown(
                                    f"⏰ {session_time}"
                                )
        
                            with col3:
        
                                st.markdown(
                                    f"📘 {topic}"
                                )
        
                                if attendance == "Present":
        
                                    st.caption(
                                        "✅ Present"
                                    )
        
                                elif attendance == "Late":
        
                                    st.caption(
                                        "⚠️ Late"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Excused"
                                ):
        
                                    st.caption(
                                        "⚠️ Excused Absence"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Unexcused"
                                ):
        
                                    st.caption(
                                        "❌ Unexcused Absence"
                                    )
        
                                else:
        
                                    st.caption(
                                        "⏳ Attendance Pending"
                                    )
        
                            with col4:
        
                                if st.button(
                                    "📖 Review",
                                    key=(
                                        "review_session_topic_"
                                        f"{student_id}_{index}"
                                    ),
                                    use_container_width=True
                                ):
        
                                    with st.spinner(
                                        "🤖 Creating your topic reference..."
                                    ):
        
                                        from modules.ai_learning_reference import (
                                            generate_learning_reference
                                        )
        
                                        result = (
                                            generate_learning_reference(
        
                                                curriculum_topic=topic,
        
                                                homework_title="",
        
                                                instructions="",
        
                                                student_grade=str(
                                                    student["grade"]
                                                )
                                            )
                                        )
        
                                    if result.get("success"):
        
                                        st.session_state[
                                            f"session_learning_"
                                            f"{student_id}_{index}"
                                        ] = result
        
                                    else:
        
                                        st.error(
                                            result.get(
                                                "error",
                                                "Unable to create topic reference."
                                            )
                                        )
        
                            # -----------------------------------------
                            # DISPLAY AI REFERENCE
                            # -----------------------------------------
        
                            session_learning = (
                                st.session_state.get(
                                    f"session_learning_"
                                    f"{student_id}_{index}"
                                )
                            )
        
                            if session_learning:
        
                                from modules.ai_learning_reference import (
                                    display_learning_reference
                                )
        
                                with st.container(
                                    border=True
                                ):
        
                                    display_learning_reference(
                                        session_learning
                                    )
        
                            # -----------------------------------------
                            # COMPACT SEPARATOR
                            # -----------------------------------------
        
                            st.markdown(
                                "<hr style='margin:1px 0 3px 0;'>",
                                unsafe_allow_html=True
                            )
        
                    # =================================================
                    # RECENT PAST SESSIONS
                    # =================================================
        
                    if not recent_past_display.empty:
        
                        st.markdown(
                            "### 🕘 Recent Sessions"
                        )
        
                        # Display oldest → newest so the
                        # recent history reads naturally.
                        recent_past_display = (
                            recent_past_display
                            .sort_values(
                                "Date",
                                ascending=True
                            )
                        )
        
                        for index, row in recent_past_display.iterrows():
        
                            # -----------------------------------------
                            # DATE
                            # -----------------------------------------
        
                            if pd.notna(row["Date"]):
        
                                session_date = (
                                    row["Date"]
                                    .strftime("%Y-%m-%d")
                                )
        
                            else:
        
                                session_date = "Unknown"
        
                            # -----------------------------------------
                            # TIME
                            # -----------------------------------------
        
                            session_time = str(
                                row["Time"]
                            ).strip()
        
                            # -----------------------------------------
                            # TOPIC
                            # -----------------------------------------
        
                            topic = str(
                                row["Topic"]
                            ).strip()
        
                            # -----------------------------------------
                            # ATTENDANCE
                            # -----------------------------------------
        
                            attendance = str(
                                row["Attendance"]
                            ).strip()
        
                            # -----------------------------------------
                            # COMPACT SESSION ROW
                            # -----------------------------------------
        
                            col1, col2, col3, col4 = st.columns(
                                [
                                    1.2,
                                    1.1,
                                    3.5,
                                    1.3
                                ]
                            )
        
                            with col1:
        
                                st.markdown(
                                    f"📅 {session_date}"
                                )
        
                            with col2:
        
                                st.markdown(
                                    f"⏰ {session_time}"
                                )
        
                            with col3:
        
                                st.markdown(
                                    f"📘 {topic}"
                                )
        
                                if attendance == "Present":
        
                                    st.caption(
                                        "✅ Present"
                                    )
        
                                elif attendance == "Late":
        
                                    st.caption(
                                        "⚠️ Late"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Excused"
                                ):
        
                                    st.caption(
                                        "⚠️ Excused Absence"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Unexcused"
                                ):
        
                                    st.caption(
                                        "❌ Unexcused Absence"
                                    )
        
                                else:
        
                                    st.caption(
                                        "⏳ Attendance Pending"
                                    )
        
                            with col4:
        
                                if st.button(
                                    "📖 Review",
                                    key=(
                                        "review_session_topic_"
                                        f"{student_id}_{index}"
                                    ),
                                    use_container_width=True
                                ):
        
                                    with st.spinner(
                                        "🤖 Creating your topic reference..."
                                    ):
        
                                        from modules.ai_learning_reference import (
                                            generate_learning_reference
                                        )
        
                                        result = (
                                            generate_learning_reference(
        
                                                curriculum_topic=topic,
        
                                                homework_title="",
        
                                                instructions="",
        
                                                student_grade=str(
                                                    student["grade"]
                                                )
                                            )
                                        )
        
                                    if result.get("success"):
        
                                        st.session_state[
                                            f"session_learning_"
                                            f"{student_id}_{index}"
                                        ] = result
        
                                    else:
        
                                        st.error(
                                            result.get(
                                                "error",
                                                "Unable to create topic reference."
                                            )
                                        )
        
                            # -----------------------------------------
                            # DISPLAY AI REFERENCE
                            # -----------------------------------------
        
                            session_learning = (
                                st.session_state.get(
                                    f"session_learning_"
                                    f"{student_id}_{index}"
                                )
                            )
        
                            if session_learning:
        
                                from modules.ai_learning_reference import (
                                    display_learning_reference
                                )
        
                                with st.container(
                                    border=True
                                ):
        
                                    display_learning_reference(
                                        session_learning
                                    )
        
                            # -----------------------------------------
                            # COMPACT SEPARATOR
                            # -----------------------------------------
        
                            st.markdown(
                                "<hr style='margin:1px 0 3px 0;'>",
                                unsafe_allow_html=True
                            )
        
                    # =================================================
                    # PREVIOUS / OLDER SESSIONS
                    # =================================================
        
                    if not remaining_past.empty:
        
                        st.markdown(
                            "### 📚 Previous Sessions"
                        )
        
                        for index, row in remaining_past.iterrows():
        
                            # -----------------------------------------
                            # DATE
                            # -----------------------------------------
        
                            if pd.notna(row["Date"]):
        
                                session_date = (
                                    row["Date"]
                                    .strftime("%Y-%m-%d")
                                )
        
                            else:
        
                                session_date = "Unknown"
        
                            # -----------------------------------------
                            # TIME
                            # -----------------------------------------
        
                            session_time = str(
                                row["Time"]
                            ).strip()
        
                            # -----------------------------------------
                            # TOPIC
                            # -----------------------------------------
        
                            topic = str(
                                row["Topic"]
                            ).strip()
        
                            # -----------------------------------------
                            # ATTENDANCE
                            # -----------------------------------------
        
                            attendance = str(
                                row["Attendance"]
                            ).strip()
        
                            # -----------------------------------------
                            # COMPACT SESSION ROW
                            # -----------------------------------------
        
                            col1, col2, col3, col4 = st.columns(
                                [
                                    1.2,
                                    1.1,
                                    3.5,
                                    1.3
                                ]
                            )
        
                            with col1:
        
                                st.markdown(
                                    f"📅 {session_date}"
                                )
        
                            with col2:
        
                                st.markdown(
                                    f"⏰ {session_time}"
                                )
        
                            with col3:
        
                                st.markdown(
                                    f"📘 {topic}"
                                )
        
                                if attendance == "Present":
        
                                    st.caption(
                                        "✅ Present"
                                    )
        
                                elif attendance == "Late":
        
                                    st.caption(
                                        "⚠️ Late"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Excused"
                                ):
        
                                    st.caption(
                                        "⚠️ Excused Absence"
                                    )
        
                                elif (
                                    attendance
                                    == "Absent - Unexcused"
                                ):
        
                                    st.caption(
                                        "❌ Unexcused Absence"
                                    )
        
                                else:
        
                                    st.caption(
                                        "⏳ Attendance Pending"
                                    )
        
                            with col4:
        
                                if st.button(
                                    "📖 Review",
                                    key=(
                                        "review_session_topic_"
                                        f"{student_id}_{index}"
                                    ),
                                    use_container_width=True
                                ):
        
                                    with st.spinner(
                                        "🤖 Creating your topic reference..."
                                    ):
        
                                        from modules.ai_learning_reference import (
                                            generate_learning_reference
                                        )
        
                                        result = (
                                            generate_learning_reference(
        
                                                curriculum_topic=topic,
        
                                                homework_title="",
        
                                                instructions="",
        
                                                student_grade=str(
                                                    student["grade"]
                                                )
                                            )
                                        )
        
                                    if result.get("success"):
        
                                        st.session_state[
                                            f"session_learning_"
                                            f"{student_id}_{index}"
                                        ] = result
        
                                    else:
        
                                        st.error(
                                            result.get(
                                                "error",
                                                "Unable to create topic reference."
                                            )
                                        )
        
                            # -----------------------------------------
                            # DISPLAY AI REFERENCE
                            # -----------------------------------------
        
                            session_learning = (
                                st.session_state.get(
                                    f"session_learning_"
                                    f"{student_id}_{index}"
                                )
                            )
        
                            if session_learning:
        
                                from modules.ai_learning_reference import (
                                    display_learning_reference
                                )
        
                                with st.container(
                                    border=True
                                ):
        
                                    display_learning_reference(
                                        session_learning
                                    )
        
                            # -----------------------------------------
                            # COMPACT SEPARATOR
                            # -----------------------------------------
        
                            st.markdown(
                                "<hr style='margin:1px 0 3px 0;'>",
                                unsafe_allow_html=True
                            )

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
                subset=["Date"]
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
                    - pd.Timedelta(
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

                    for index, row in (
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
                                    + session_date.strftime(
                                        "%A, %b %d, %Y"
                                    )
                                )

                            with c2:

                                st.write(
                                    "⏰ "
                                    + str(
                                        session_time
                                    )
                                )

                            with c3:

                                st.write(
                                    "📘 "
                                    + (
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
                            and str(
                                zoom_link
                            ).strip()
                            not in [
                                "",
                                "nan",
                                "None"
                            ]
                        ):

                            st.markdown(
                                f"🔗 "
                                f"[Join Zoom Classroom]"
                                f"({zoom_link})"
                            )

                        elif (
                            meeting_id
                            and str(
                                meeting_id
                            ).strip()
                            not in [
                                "",
                                "nan",
                                "None"
                            ]
                        ):

                            st.info(
                                f"Zoom Meeting ID: "
                                f"{meeting_id}"
                            )
