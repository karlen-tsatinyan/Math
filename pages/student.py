import streamlit as st
import pandas as pd

from utils.datetime_utils import today_str
from database import query_dataframe


# ============================================================
# CACHE SETTINGS
# ============================================================

CACHE_TTL = 300  # 5 minutes


# ============================================================
# STUDENT ID RESOLUTION
# ============================================================

def get_student_id():

    user = st.session_state.get("user", {})

    # --------------------------------------------------------
    # Preferred method: student_id stored in logged-in user
    # --------------------------------------------------------

    student_id = user.get("student_id")

    if student_id is not None:

        try:
            return int(student_id)

        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # Fallback: resolve using user ID
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
    # Final fallback: resolve using username
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
#
# IMPORTANT:
# This is intentionally NOT cached.
# ============================================================

def get_student_info(student_id):

    if not student_id:
        return pd.DataFrame()

    try:

        return query_dataframe(
            """
            SELECT
                id,
                COALESCE(first_name, '') AS first_name,
                COALESCE(last_name, '') AS last_name,
                COALESCE(grade, 'N/A') AS grade,
                COALESCE(subject, 'N/A') AS subject,
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

@st.cache_data(ttl=CACHE_TTL)
def get_dashboard_data(student_id, today_date):

    homework_due = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM homework
        WHERE student_id = %s
          AND status = 'Assigned'
          AND archived = 0
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
            s.topic,
            st.zoom_link
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
# PERFORMANCE DATA
# ============================================================

@st.cache_data(ttl=CACHE_TTL)
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
          AND archived = 0
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

@st.cache_data(ttl=CACHE_TTL)
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
            ON a.student_id = s.student_id
            AND a.session_date = s.session_date
            AND a.session_time = s.session_time

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

@st.cache_data(ttl=CACHE_TTL)
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

@st.cache_data(ttl=CACHE_TTL)
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
    # STUDENT INFORMATION
    # ========================================================

    student_df = get_student_info(student_id)

    if student_df.empty:

        st.error(
            f"No student record found for Student ID: {student_id}"
        )

        return

    student = student_df.iloc[0]

    # ========================================================
    # SIDEBAR CSS
    # ========================================================

    st.sidebar.markdown(
        """
        <style>

        /* ================================================
           STUDENT PORTAL TITLE
           ================================================ */

        .student-portal-title {

            font-size: 1.10rem;

            font-weight: 700;

            margin-top: -8px;
            margin-bottom: 7px;

            padding: 0;

            line-height: 1.1;
        }


        /* ================================================
           SECTION HEADINGS
           ================================================ */

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


        /* ================================================
           NAVIGATION BUTTONS
           ================================================ */

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


        /* ================================================
           REMOVE EXCESS SPACING
           ================================================ */

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
    # CURRENT MENU STATE
    # ========================================================

    valid_student_options = [

        "🏠 Dashboard",

        "📚 Homework",

        "📊 Performance",

        "📅 Schedule",

        "💰 Financial Statements"

    ]

    if "student_portal_menu" not in st.session_state:

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
    # NAVIGATION BUTTON FUNCTION
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

            st.session_state.student_portal_menu = value

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

    z_link = student.get("zoom_link")

    m_id = student.get("meeting_id")

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
            not in ["", "nan", "None"]
        ):

            st.sidebar.markdown(
                f"🔗 [General Zoom Room]({z_link})"
            )

        if (
            m_id
            and str(m_id).strip()
            not in ["", "nan", "None"]
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

        st.markdown(
            f"""
            <div style="
                padding: 10px 16px;
                border-radius: 6px;
                background-color: rgba(0, 128, 0, 0.08);
                border: 1px solid rgba(0, 128, 0, 0.20);
                font-size: 16px;
            ">
                <strong>
                    Welcome {student['first_name']} {student['last_name']}
                </strong>
        
                <span style="display:inline-block; width:1in;"></span>
        
                <strong>
                    Grade: {student['grade']}
                </strong>
        
                <span style="display:inline-block; width:1in;"></span>
        
                <strong>
                    Subject: {student['subject']}
                </strong>
            </div>
            """,
            unsafe_allow_html=True
        )

        dashboard = get_dashboard_data(
            student_id,
            today_str()
        )

        homework_due = dashboard["homework_due"]

        sessions_count = dashboard["sessions_count"]

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
            "📅 Total Upcoming",
            sess_total
        )

        st.divider()

        # ====================================================
        # NEXT UPCOMING SESSION
        # ====================================================

        st.subheader(
            "Next Upcoming Session"
        )

        next_session = dashboard["next_session"]

        if not next_session.empty:

            s = next_session.iloc[0]

            session_date = s["session_date"]

            session_time = s["session_time"]

            topic = s["topic"]

            st.info(
                f"**Date:** {session_date} "
                f"at {session_time} | "
                f"**Topic:** {topic}"
            )

            zoom_url = s.get("zoom_link")

            if (
                zoom_url
                and str(zoom_url).strip()
                not in ["", "nan", "None"]
            ):

                st.markdown(
                    f"🔗 [Join Zoom Meeting]({zoom_url})"
                )

            else:

                st.caption(
                    "No Zoom link assigned for this session yet."
                )

        else:

            st.write(
                "No upcoming sessions scheduled."
            )

    # ========================================================
    # HOMEWORK
    # ========================================================

    elif option == "📚 Homework":

        from modules.homework import student_homework

        student_homework()

    # ========================================================
    # PERFORMANCE
    #
    # IMPORTANT:
    # We intentionally use a radio selector rather than
    # st.tabs().
    #
    # st.tabs() executes the contents of ALL tabs on every
    # rerun. The radio selector executes only the selected
    # Performance section.
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

        if performance_section == "📚 Homework Grades":

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
        # ADVANCED PROGRESSION ANALYTICS
        # ====================================================

        elif (
            performance_section
            == "📈 Advanced Progression Analytics"
        ):

            st.subheader(
                "📈 Advanced Progression Analytics"
            )

            st.caption(
                "Progression is based on homework due dates, "
                "not submission dates or grading dates."
            )

            try:

                from modules.performance import (
                    student_performance_view
                )

                student_performance_view(
                    int(student_id)
                )

            except Exception as e:

                st.error(
                    "Unable to load Performance Analytics."
                )

                st.exception(e)

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

                sessions = sessions_history[
                    [
                        "Date",
                        "Time",
                        "Topic",
                        "Attendance"
                    ]
                ]

                st.dataframe(
                    sessions,
                    use_container_width=True,
                    hide_index=True
                )

    # ========================================================
    # FINANCIAL STATEMENTS
    # ========================================================

    elif option == "💰 Financial Statements":

        # IMPORTANT:
        # Preserve current page before entering module.

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
            "📅 My Sessions"
        )

        sessions = get_session_history(
            student_id
        )

        if sessions.empty:

            st.info(
                "No sessions found."
            )

        else:

            sessions["Date"] = pd.to_datetime(
                sessions["Date"],
                errors="coerce"
            )

            today = pd.to_datetime(
                today_str()
            )

            # ------------------------------------------------
            # SESSION FILTER
            # ------------------------------------------------

            filter_option = st.selectbox(
                "Show Sessions",
                [
                    "Recent 5 + Upcoming 3 (Default)",
                    "Last 10 Sessions",
                    "Last 30 Days",
                    "All Sessions"
                ],
                key="student_session_filter"
            )

            # ------------------------------------------------
            # DEFAULT
            # ------------------------------------------------

            if (
                filter_option
                == "Recent 5 + Upcoming 3 (Default)"
            ):

                recent = (

                    sessions[
                        sessions["Date"] <= today
                    ]

                    .sort_values(
                        ["Date", "Time"],
                        ascending=False
                    )

                    .head(5)
                )

                upcoming = (

                    sessions[
                        sessions["Date"] > today
                    ]

                    .sort_values(
                        ["Date", "Time"]
                    )

                    .head(3)
                )

                sessions_display = pd.concat(
                    [
                        upcoming,
                        recent
                    ]
                )

            # ------------------------------------------------
            # LAST 10
            # ------------------------------------------------

            elif filter_option == "Last 10 Sessions":

                sessions_display = (

                    sessions

                    .sort_values(
                        ["Date", "Time"],
                        ascending=False
                    )

                    .head(10)
                )

            # ------------------------------------------------
            # LAST 30 DAYS
            # ------------------------------------------------

            elif filter_option == "Last 30 Days":

                start_date = (
                    today
                    - pd.Timedelta(days=30)
                )

                sessions_display = sessions[
                    sessions["Date"] >= start_date
                ]

            # ------------------------------------------------
            # ALL SESSIONS
            # ------------------------------------------------

            else:

                sessions_display = (

                    sessions

                    .sort_values(
                        ["Date", "Time"],
                        ascending=False
                    )
                )

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

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

                    "Date": "📅 Date",

                    "Time": "⏰ Time",

                    "Topic": "📘 Topic",

                    "Attendance": "✅ Attendance"

                }
            )
