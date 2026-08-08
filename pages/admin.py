from datetime import date

import pandas as pd
import streamlit as st

from database import query_dataframe

from modules.attendance import attendance_management
from modules.curriculum import curriculum_management
from modules.payments import payment_management
from modules.performance import performance_dashboard
from modules.reports import reports_management
from modules.scheduler import scheduler_management
from modules.student_profile import student_profile
from modules.students import student_management
from modules.homework import homework_management, archived_homework
from modules.archived_students import archived_students

from utils.datetime_utils import today_str


# ============================================================
# PAGE / CACHE SETTINGS
# ============================================================

CACHE_TTL = 300  # 5 minutes


# ============================================================
# HIDE STREAMLIT UI ELEMENTS
# ============================================================

st.markdown(
    """
    <style>

    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    header [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD — CACHED DATA
# ============================================================

@st.cache_data(ttl=CACHE_TTL)
def get_student_count():

    return query_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM students
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def get_homework_waiting_count():

    return query_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM homework
        WHERE status = 'Submitted'
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def get_homework_due_count():

    return query_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM homework
        WHERE status = 'Assigned'
          AND archived = 0
        """
    )


@st.cache_data(ttl=CACHE_TTL)
def get_today_session_count(today_date):

    return query_dataframe(
        """
        SELECT COUNT(*) AS total
        FROM sessions
        WHERE session_date = %s
        """,
        (today_date,),
    )


@st.cache_data(ttl=CACHE_TTL)
def get_today_schedule(today_date):

    return query_dataframe(
        """
        SELECT
            s.first_name,
            s.last_name,
            ss.session_time,
            ss.topic,
            s.zoom_link,
            ss.notes
        FROM sessions ss
        JOIN students s
            ON ss.student_id = s.id
        WHERE ss.session_date = %s
        ORDER BY ss.session_time
        """,
        (today_date,),
    )


@st.cache_data(ttl=CACHE_TTL)
def get_upcoming_sessions(today_date):

    return query_dataframe(
        """
        SELECT
            s.first_name || ' ' || s.last_name AS "Student",
            ss.session_date AS "Date",
            ss.session_time AS "Time",
            ss.topic AS "Lesson"
        FROM sessions ss
        JOIN students s
            ON ss.student_id = s.id
        WHERE ss.session_date > %s
        ORDER BY
            ss.session_date,
            ss.session_time
        LIMIT 10
        """,
        (today_date,),
    )


@st.cache_data(ttl=CACHE_TTL)
def get_waiting_homework():

    return query_dataframe(
        """
        SELECT
            s.first_name || ' ' || s.last_name AS "Student",
            h.created_at AS "Submitted Date"
        FROM homework h
        JOIN students s
            ON h.student_id = s.id
        WHERE h.status = 'Submitted'
        ORDER BY h.created_at DESC
        """
    )


# ============================================================
# DASHBOARD
# ============================================================

def show_dashboard():

    st.title("📊 Math Tutoring Dashboard")

    today_date = today_str()


    # --------------------------------------------------------
    # KPI DATA
    # --------------------------------------------------------

    student_count = get_student_count()

    today_sessions = get_today_session_count(
        today_date
    )

    homework_waiting = get_homework_waiting_count()

    homework_due = get_homework_due_count()


    # --------------------------------------------------------
    # SAFE KPI VALUES
    # --------------------------------------------------------

    student_total = (
        int(student_count.iloc[0]["total"])
        if not student_count.empty
        else 0
    )

    session_total = (
        int(today_sessions.iloc[0]["total"])
        if not today_sessions.empty
        else 0
    )

    waiting_total = (
        int(homework_waiting.iloc[0]["total"])
        if not homework_waiting.empty
        else 0
    )

    due_total = (
        int(homework_due.iloc[0]["total"])
        if not homework_due.empty
        else 0
    )


    # --------------------------------------------------------
    # KPI DISPLAY
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)


    col1.metric(
        "👨‍🎓 Students",
        student_total
    )


    col2.metric(
        "📅 Today's Sessions",
        session_total
    )


    col3.metric(
        "📚 Homework Waiting",
        waiting_total
    )


    col4.metric(
        "📝 Homework Due",
        due_total
    )


    st.divider()


    # ========================================================
    # TODAY'S SCHEDULE
    # ========================================================

    st.subheader(
        "📅 Today's Schedule"
    )


    today = get_today_schedule(
        today_date
    )


    if today.empty:

        st.info(
            "There is no session for today."
        )

    else:

        for _, row in today.iterrows():

            with st.container(border=True):

                student_name = (
                    f"{row['first_name']} "
                    f"{row['last_name']}"
                )

                session_time = row["session_time"]

                lesson_topic = row["topic"]

                zoom_url = row["zoom_link"]

                notes = row["notes"]


                st.write(
                    f"""
                    **Student:** {student_name}

                    **Time:** {
                        session_time
                        if session_time
                        else "Not Set"
                    }

                    **Lesson:** {
                        lesson_topic
                        if lesson_topic
                        else "Not Entered"
                    }
                    """
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


                if (
                    notes
                    and str(notes).strip()
                    not in [
                        "",
                        "nan",
                        "None"
                    ]
                ):

                    st.caption(
                        f"📝 Notes: {notes}"
                    )


                st.divider()


    # ========================================================
    # UPCOMING SESSIONS
    # ========================================================

    st.subheader(
        "📅 Upcoming Sessions"
    )


    upcoming = get_upcoming_sessions(
        today_date
    )


    if upcoming.empty:

        st.info(
            "No upcoming sessions."
        )

    else:

        st.dataframe(
            upcoming,
            hide_index=True,
            use_container_width=True
        )


    # ========================================================
    # HOMEWORK WAITING
    # ========================================================

    st.subheader(
        "📚 Homework Waiting For Review"
    )


    waiting = get_waiting_homework()


    if waiting.empty:

        st.success(
            "Nothing waiting 🎉"
        )

    else:

        st.dataframe(
            waiting,
            hide_index=True,
            use_container_width=True
        )


    # ========================================================
    # STUDENT SEARCH
    # ========================================================

    st.subheader(
        "🔍 Student Search"
    )


    keyword = st.text_input(
        "Search by name",
        key="admin_student_search"
    )


    if keyword.strip():

        search_text = (
            keyword.strip()
        )


        results = query_dataframe(
            """
            SELECT
                first_name,
                last_name,
                grade,
                subject
            FROM students
            WHERE
                LOWER(first_name)
                LIKE LOWER(%s)
                OR
                LOWER(last_name)
                LIKE LOWER(%s)
            ORDER BY
                first_name,
                last_name
            """,
            (
                f"%{search_text}%",
                f"%{search_text}%"
            ),
        )


        if results.empty:

            st.info(
                "No students found."
            )

        else:

            st.dataframe(
                results,
                hide_index=True,
                use_container_width=True
            )


    # ========================================================
    # QUICK ACTIONS
    # ========================================================

    st.subheader(
        "⚡ Quick Actions"
    )


    col1, col2, col3, col4 = st.columns(4)


    with col1:

        if st.button(
            "➕ Add Student",
            use_container_width=True,
            key="quick_add_student"
        ):

            st.session_state.admin_option = (
                "Students"
            )

            st.rerun()


    with col2:

        if st.button(
            "📅 Schedule",
            use_container_width=True,
            key="quick_schedule"
        ):

            st.session_state.admin_option = (
                "Schedule"
            )

            st.rerun()


    with col3:

        if st.button(
            "💰 Payment",
            use_container_width=True,
            key="quick_payment"
        ):

            st.session_state.admin_option = (
                "Payments"
            )

            st.rerun()


    with col4:

        if st.button(
            "📚 Homework",
            use_container_width=True,
            key="quick_homework"
        ):

            st.session_state.admin_option = (
                "Homework"
            )

            st.rerun()


# ============================================================
# MAIN ADMIN PAGE
# ============================================================

def admin_page():

    st.sidebar.title(
        "Admin Control Panel"
    )


    # ========================================================
    # ADMIN MENU STRUCTURE
    # ========================================================

    menu_options = [

        # ----------------------------
        # ACADEMICS
        # ----------------------------

        "🏠 Dashboard",

        "👨‍🎓 Students",

        "👤 Student Profiles",

        "📚 Homework",

        "📅 Schedule",

        "📋 Attendance",


        # ----------------------------
        # FINANCE
        # ----------------------------

        "💰 Payments",

        "📈 Student Financials",

        "📊 Reports",


        # ----------------------------
        # SYSTEM
        # ----------------------------

        "📦 Archived Homework",

        "👨‍🎓 Archived Students",

    ]


    # ========================================================
    # CURRENT MENU STATE
    # ========================================================

    if "admin_option" not in st.session_state:

        st.session_state.admin_option = (
            "🏠 Dashboard"
        )


    if (
        st.session_state.admin_option
        not in menu_options
    ):

        st.session_state.admin_option = (
            "🏠 Dashboard"
        )


    option = st.sidebar.radio(

        "Admin Menu",

        menu_options,

        index=menu_options.index(
            st.session_state.admin_option
        ),

        key="admin_menu_radio"

    )


    st.session_state.admin_option = option



    # ========================================================
    # ROUTING
    # ========================================================


    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    if option == "🏠 Dashboard":

        show_dashboard()



    # --------------------------------------------------------
    # STUDENTS
    # --------------------------------------------------------

    elif option == "👨‍🎓 Students":

        student_management()



    # --------------------------------------------------------
    # STUDENT PROFILES
    # --------------------------------------------------------

    elif option == "👤 Student Profiles":

        student_profile()



    # --------------------------------------------------------
    # HOMEWORK
    # --------------------------------------------------------
    
    elif option == "📚 Homework":
    
        homework_management()




    # --------------------------------------------------------
    # SCHEDULE
    # --------------------------------------------------------

    elif option == "📅 Schedule":

        scheduler_management()



    # --------------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------------

    elif option == "📋 Attendance":

        attendance_management()



    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    elif option == "💰 Payments":

        payment_management()



    # --------------------------------------------------------
    # STUDENT FINANCIALS
    # --------------------------------------------------------

    elif option == "📈 Student Financials":

        financial_dashboard()



    # --------------------------------------------------------
    # REPORTS
    # --------------------------------------------------------

    elif option == "📊 Reports":

        reports_management()



    # --------------------------------------------------------
    # ARCHIVED HOMEWORK
    # --------------------------------------------------------
    
    elif option == "📦 Archived Homework":
    
        archived_homework()


    # --------------------------------------------------------
    # ARCHIVED STUDENTS
    # --------------------------------------------------------

    elif option == "👨‍🎓 Archived Students":

        archived_students()


    # ========================================================
    # LIVE CURRICULUM BOARD
    # ========================================================    
    
    elif option == "📘 Live Curriculum Board":
    
        curriculum_management()

