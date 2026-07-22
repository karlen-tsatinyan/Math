import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date
from utils.datetime_utils import today_str

from modules.student_profile import student_profile
from modules.performance import performance_dashboard
from modules.curriculum import curriculum_management

from database import query_dataframe
from modules.students import student_management
from modules.payments import payment_management
from modules.homework import homework_management

from modules.scheduler import scheduler_management
from modules.attendance import attendance_management

from modules.reports import reports_management
from database import query_dataframe



def admin_page():
    # Hide the default Streamlit multi-page auto-generated sidebar navigation header
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.sidebar.button(
        "🔄 Refresh",
        use_container_width=True
    ):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()


    st.sidebar.title(
        "Admin Control Panel"
    )


    default_option = st.session_state.get(
    "admin_option",
    "Dashboard"
)


    menu_options = [

        "Dashboard",
        "Students",
        "Student Profile",
        "Performance",
        "Payments",
        "Homework",
        "Schedule",
        "Attendance",
        "Live Curriculum Board",
        "Reports"

    ]

    if default_option not in menu_options:
        default_option = "Dashboard"

    option = st.sidebar.radio(

        "Admin Menu",

        menu_options,

        index=menu_options.index(default_option)

    )


    st.session_state.admin_option=option


    if option == "Dashboard":

        st.title("📊 Math Tutoring Dashboard")

        # ----------------------------
        # KPI Queries
        # ----------------------------

        student_count = query_dataframe("""
            SELECT COUNT(*) AS total
            FROM students
        """)

        payment_total = query_dataframe("""
            SELECT
                COALESCE(SUM(amount),0) AS total
            FROM payments
        """)

        homework_waiting = query_dataframe("""
            SELECT COUNT(*) AS total
            FROM homework
            WHERE status='Submitted'
        """)

        homework_due = query_dataframe(
            """
            SELECT COUNT(*) total

            FROM homework

            WHERE

                status='Assigned'

                AND archived=0
            """
        )

        today_date = today_str()
        today_sessions = query_dataframe(
            """
            SELECT COUNT(*) AS total
            FROM sessions
            WHERE session_date=?
            """,
            (today_str(),)
)

        col1,col2,col3,col4, col5 = st.columns(5)

        col1.metric(
            "👨‍🎓 Students",
            int(student_count.iloc[0]["total"])
        )

        col2.metric(
            "📅 Today's Sessions",
            int(today_sessions.iloc[0]["total"])
        )

        col3.metric(
            "💰 Revenue",
            f"${payment_total.iloc[0]['total']:,.2f}"
        )

        col4.metric(
            "📚 Homework Waiting",
            int(homework_waiting.iloc[0]["total"])
        )

        col5.metric(

            "📝 Homework Due",

            int(homework_due.iloc[0]["total"])

        )
                
        st.divider()

        # ============================
        # TODAY'S SCHEDULE
        # ============================

        st.subheader("📅 Today's Schedule")

        today = query_dataframe(
            """
            SELECT
                s.first_name || ' ' || s.last_name AS Student,
                ss.session_time AS Time,
                ss.topic AS Lesson,
                ss.zoom_link AS Zoom,
                ss.notes AS Notes
            FROM sessions ss
            JOIN students s
            ON ss.student_id=s.id
            WHERE ss.session_date = ?
            ORDER BY ss.session_time
            """,
            (
                today_str(),
            )
        )

        if today.empty or len(today) == 0:
            st.info("There is no session for today.")
        else:
            for _, row in today.iterrows():
                with st.container():
                    student_name = row.get('Student', row.get('student', 'N/A'))
                    session_time = row.get('Time', row.get('session_time', 'N/A'))
                    lesson_topic = row.get('Lesson', row.get('topic', 'N/A'))
                    zoom_url = row.get('Zoom', row.get('zoom_link', ''))
                    notes = row.get('Notes', row.get('notes', ''))

                    st.write(f"**Student:** {student_name} | **Time:** {session_time} | **Lesson:** {lesson_topic}")
                    
                    if zoom_url and str(zoom_url).strip() not in ["", "nan", "None"]:
                        st.markdown(f"🔗 [Join Zoom Meeting]({zoom_url})")
                        
                    if notes and str(notes).strip() not in ["", "nan", "None"]:
                        st.caption(f"📝 Notes: {notes}")
                        
                    st.divider()


        # ============================
        # UPCOMING SESSIONS
        # ============================

        st.subheader(
            "📅 Upcoming Sessions"
        )

        upcoming = query_dataframe(
            """

            SELECT

                s.first_name || ' ' || s.last_name AS Student,

                ss.session_date AS Date,

                ss.session_time AS Time,

                ss.topic AS Lesson


            FROM sessions ss


            JOIN students s


            ON ss.student_id=s.id


            WHERE ss.session_date > ?


            ORDER BY ss.session_date, ss.session_time


            LIMIT 10

            """,
            (
                today_str(),
            )
        )

        if len(upcoming)==0:

            st.info(
                "No upcoming sessions."
            )

        else:

            st.dataframe(

                upcoming,

                hide_index=True,

                use_container_width=True

            )

        st.subheader("📚 Homework Waiting For Review")

        waiting=query_dataframe("""

        SELECT

        s.first_name || ' ' || s.last_name AS Student,

        h.created_at AS Submitted_Date

        FROM homework h

        JOIN students s

        ON h.student_id=s.id

        WHERE h.status='Submitted'

        ORDER BY h.created_at DESC

        """)


        if len(waiting)==0:

            st.success("Nothing waiting 🎉")

        else:

            st.dataframe(
                waiting,
                hide_index=True,
                use_container_width=True
            )


        st.subheader("🔍 Student Search")

        keyword=st.text_input(
            "Search by name"
        )

        if keyword:

            results=query_dataframe("""

            SELECT

            first_name,

            last_name,

            grade,

            subject

            FROM students

            WHERE

            first_name LIKE ?

            OR

            last_name LIKE ?

            """,

            (

            f"%{keyword}%",

            f"%{keyword}%"

            )

            )

            st.dataframe(
                results,
                hide_index=True,
                use_container_width=True
            )
        st.subheader(
            "⚡ Quick Actions"
        )


        col1,col2,col3,col4=st.columns(4)


        with col1:

            if st.button(
                "➕ Add Student"
            ):

                st.session_state.admin_option="Students"

                st.rerun()



        with col2:

            if st.button(
                "📅 Schedule"
            ):

                st.session_state.admin_option="Schedule"

                st.rerun()



        with col3:

            if st.button(
                "💰 Payment"
            ):

                st.session_state.admin_option="Payments"

                st.rerun()



        with col4:

            if st.button(
                "📚 Homework"
            ):

                st.session_state.admin_option="Homework"

                st.rerun()
                

    elif option=="Students":

        student_management()

    elif option=="Student Profile":

        student_profile()

    elif option=="Payments":

        payment_management()

    elif option == "Performance":

        performance_dashboard()

    elif option=="Homework":

        homework_management()



    elif option=="Schedule":

        scheduler_management()


    elif option=="Attendance":

        attendance_management()

    elif option == "Live Curriculum Board":

        curriculum_management()


    elif option=="Reports":

        reports_management()
