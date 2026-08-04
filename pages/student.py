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

    # Preferred method:
    # student_id should already be attached to logged-in user
    student_id = user.get("student_id")

    if student_id is not None:

        try:
            return int(student_id)

        except (ValueError, TypeError):
            pass

    # Fallback only if student_id is not already available
    user_id = user.get("id")

    if user_id:

        result = query_dataframe(
            """
            SELECT student_id
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

    # Final fallback using username
    username = user.get("username")

    if username:

        result = query_dataframe(
            """
            SELECT student_id
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

    return None


# ============================================================
# STUDENT INFORMATION
# ============================================================

@st.cache_data(ttl=CACHE_TTL)
def get_student_info(student_id):

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
        (student_id,)
    )


# ============================================================
# DASHBOARD DATA
# ============================================================

@st.cache_data(ttl=CACHE_TTL)
def get_dashboard_data(student_id, today_date):

    homework_due = query_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM homework
        WHERE student_id = %s
          AND status = 'Assigned'
          AND archived = 0
        """,
        (student_id,)
    )

    sessions_count = query_dataframe(
        """
        SELECT COUNT(*) AS total
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
            COALESCE(SUM(amount), 0) AS total
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
          AND grade IS NOT NULL
          AND TRIM(grade) <> ''
        ORDER BY due_date DESC
        """,
        (student_id,)
    )


@st.cache_data(ttl=CACHE_TTL)
@st.cache_data(ttl=CACHE_TTL)
def get_session_history(student_id, view="Recent 5 + Upcoming 3"):

    if view == "Recent 5 + Upcoming 3":

        recent = query_dataframe(
            """
            SELECT
                s.session_date AS "Date",
                s.session_time AS "Time",
                s.topic AS "Topic",
                COALESCE(a.status, 'Pending') AS "Attendance"
            FROM sessions s

            LEFT JOIN attendance a
                ON a.student_id = s.student_id
                AND a.session_date = s.session_date

            WHERE s.student_id = %s
              AND s.session_date < CURRENT_DATE

            ORDER BY
                s.session_date DESC,
                s.session_time DESC

            LIMIT 5
            """,
            (student_id,)
        )


        upcoming = query_dataframe(
            """
            SELECT
                s.session_date AS "Date",
                s.session_time AS "Time",
                s.topic AS "Topic",
                'Upcoming' AS "Attendance"
            FROM sessions s

            WHERE s.student_id = %s
              AND s.session_date >= CURRENT_DATE

            ORDER BY
                s.session_date ASC,
                s.session_time ASC

            LIMIT 3
            """,
            (student_id,)
        )


        return pd.concat(
            [
                upcoming,
                recent
            ],
            ignore_index=True
        )


    elif view == "Last 10 Sessions":

        return query_dataframe(
            """
            SELECT
                s.session_date AS "Date",
                s.session_time AS "Time",
                s.topic AS "Topic",
                COALESCE(a.status,'Pending') AS "Attendance"

            FROM sessions s

            LEFT JOIN attendance a
                ON a.student_id = s.student_id
                AND a.session_date = s.session_date

            WHERE s.student_id = %s

            ORDER BY
                s.session_date DESC,
                s.session_time DESC

            LIMIT 10
            """,
            (student_id,)
        )


    elif view == "Last 30 Days":

        return query_dataframe(
            """
            SELECT
                s.session_date AS "Date",
                s.session_time AS "Time",
                s.topic AS "Topic",
                COALESCE(a.status,'Pending') AS "Attendance"

            FROM sessions s

            LEFT JOIN attendance a
                ON a.student_id = s.student_id
                AND a.session_date = s.session_date

            WHERE s.student_id = %s
              AND s.session_date >= CURRENT_DATE - INTERVAL '30 days'

            ORDER BY
                s.session_date DESC,
                s.session_time DESC
            """,
            (student_id,)
        )


    else:

        return query_dataframe(
            """
            SELECT
                s.session_date AS "Date",
                s.session_time AS "Time",
                s.topic AS "Topic",
                COALESCE(a.status,'Pending') AS "Attendance"

            FROM sessions s

            LEFT JOIN attendance a
                ON a.student_id = s.student_id
                AND a.session_date = s.session_date

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
        ORDER BY payment_date DESC
        """,
        (student_id,)
    )


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

    # --------------------------------------------------------
    # Resolve Student
    # --------------------------------------------------------

    student_id = get_student_id()

    if not student_id:

        st.error(
            "No linked student profile found for this user account. "
            "Please check with your administrator."
        )

        return


    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    st.sidebar.title("Student Portal")

    option = st.sidebar.radio(
        "Menu",
        [
            "Dashboard",
            "Homework",
            "Performance",
            "Financial Statements",
            "Schedule"
        ],
        key="student_portal_menu"
    )


    # --------------------------------------------------------
    # Manual Refresh
    # --------------------------------------------------------

    st.sidebar.divider()

    if st.sidebar.button(
        "🔄 Refresh Data",
        use_container_width=True,
        key="student_manual_refresh"
    ):

        # Clear cached database results
        st.cache_data.clear()

        st.rerun()


    # --------------------------------------------------------
    # Student Information
    #
    # This is cached and used by multiple sections.
    # --------------------------------------------------------

    student_df = get_student_info(student_id)


    if student_df.empty:

        st.error(
            f"No student record found for Student ID: {student_id}"
        )

        return


    student = student_df.iloc[0]


    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    if option == "Dashboard":

        st.title("Student Dashboard")


        st.success(
            f"Welcome {student['first_name']} \t\t"
            f"{student['last_name']} &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; "
            f"Grade: {student['grade']} &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; "
            f"Subject: {student['subject']}"
        )


        # Only Dashboard data is loaded here
        dashboard = get_dashboard_data(
            student_id,
            today_str()
        )


        homework_due = dashboard["homework_due"]

        sessions_count = dashboard["sessions_count"]

        # payments_summary = dashboard["payments_summary"]


        hw_total = (
            int(homework_due.iloc[0]["total"])
            if not homework_due.empty
            else 0
        )


        sess_total = (
            int(sessions_count.iloc[0]["total"])
            if not sessions_count.empty
            else 0
        )

        '''
        pay_total = (
            float(payments_summary.iloc[0]["total"])
            if not payments_summary.empty
            else 0.0
        )
        '''

        c1, c2 = st.columns(2)


        c1.metric(
            "📚 Homework Due",
            hw_total
        )


        c2.metric(
            "📅 Total Upcoming",
            sess_total
        )

        '''
        c3.metric(
            "💰 Payments Made",
            f"${pay_total:,.2f}"
        )
        '''

        st.divider()


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

    elif option == "Homework":

        from modules.homework import student_homework

        student_homework()


    # ========================================================
    # PERFORMANCE
    # ========================================================

    elif option == "Performance":

        st.title(
            "📊 Performance"
        )


        tab_grades, tab_analytics, tab_sessions = st.tabs(
            [
                "📚 Homework Grades",
                "📈 Advanced Progression Analytics",
                "📅 Session History"
            ]
        )


        # ----------------------------------------------------
        # HOMEWORK GRADES
        # ----------------------------------------------------

        with tab_grades:

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

        # ----------------------------------------------------
        # ADVANCED PROGRESSION ANALYTICS
        # ----------------------------------------------------
        with tab_analytics:

            from modules.performance import student_performance_view
        
            student_performance_view(
                student_id
            )

        
        # ----------------------------------------------------
        # SESSION HISTORY
        # ----------------------------------------------------

        with tab_sessions:

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
                        "Duration",
                        "Topic",
                        "Status"
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
    
    elif option == "Financial Statements":
    
        from modules.student_financials import (
            student_financials
        )
    
        student_financials()
    # ========================================================
    # SCHEDULE
    # ========================================================

    elif option == "Schedule":

        st.title(
            "My Sessions"
        )


        # Only session history is loaded here
        session_filter = st.selectbox(
            "Show Sessions",
            [
                "Recent 5 + Upcoming 3",
                "Last 10 Sessions",
                "Last 30 Days",
                "All History"
            ],
            key="student_session_filter"
        )
        
        
        sessions = get_session_history(
            student_id,
            session_filter
        )


        if sessions.empty:

            st.info(
                "No sessions found."
            )

        else:

            for _, row in sessions.iterrows():

                with st.container():

                    att_status = row.get(
                        "attendance_status",
                        "Pending"
                    )


                    if att_status == "Present":

                        badge = "✅ **Present**"

                    elif att_status == "Absent":

                        badge = "❌ **Absent**"

                    elif att_status == "Late":

                        badge = "⚠️ **Late**"

                    else:

                        badge = (
                            "⏳ **Pending / Not Marked**"
                        )


                    st.write(
                        f"📅 **Date:** {row['Date']} "
                        f"at {row['Time']} | "
                        f"**Topic:** {row.get('Topic', 'N/A')} | "
                        f"**Attendance:** {badge}"
                    )


                    if row.get("notes"):

                        st.caption(
                            f"📝 Notes: {row['notes']}"
                        )


                    st.divider()


        # ----------------------------------------------------
        # PERMANENT CLASSROOM INFO
        # ----------------------------------------------------

        z_link = student.get(
            "zoom_link"
        )

        m_id = student.get(
            "meeting_id"
        )


        if (
            z_link
            or m_id
        ):

            st.sidebar.divider()

            st.sidebar.subheader(
                "Permanent Classroom Info"
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

                st.sidebar.text(
                    f"Meeting ID: {m_id}"
                )
