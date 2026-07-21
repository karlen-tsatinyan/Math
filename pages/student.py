import streamlit as st
from utils.datetime_utils import today_str
from database import execute, query_dataframe

def student_page():
    student_id = st.session_state.user["student_id"]
    st.sidebar.title("Student Portal")
    option = st.sidebar.radio("Menu", ["Dashboard", "Homework", "Schedule", "Payments"])

    # ==========================
    # DASHBOARD
    # ==========================
    if option == "Dashboard":
        st.title("Student Dashboard")
        student = query_dataframe("SELECT first_name, last_name, grade, subject FROM students WHERE id=?", (student_id,))
        
        if len(student) > 0:
            row = student.iloc[0]
            st.success(f"Welcome {row['first_name']} {row['last_name']} | Grade: {row['grade']} | Subject: {row['subject']}")

            # Fetch KPIs
            homework_due = query_dataframe("SELECT COUNT(*) AS total FROM homework WHERE student_id=? AND status='Assigned' AND archived=0", (student_id,))
            sessions_count = query_dataframe("SELECT COUNT(*) AS total FROM sessions WHERE student_id=? AND session_date >= ?", (student_id, today_str()))
            payments = query_dataframe("SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE student_id=?", (student_id,))

            # Fetch Single Next Session
            next_session = query_dataframe(
                """SELECT session_date, session_time, topic FROM sessions 
                   WHERE student_id=? AND session_date >= ? 
                   ORDER BY session_date ASC, session_time ASC LIMIT 1""",
                (student_id, today_str())
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("📚 Homework Due", int(homework_due.iloc[0]["total"]))
            c2.metric("📅 Total Upcoming", int(sessions_count.iloc[0]["total"]))
            c3.metric("💰 Payments Made", f"${payments.iloc[0]['total']:,.2f}")
            
            st.divider()
            st.subheader("Next Upcoming Session")
            if not next_session.empty:
                s = next_session.iloc[0]
                st.info(f"**Date:** {s['session_date']} at {s['session_time']} | **Topic:** {s['topic']}")
            else:
                st.write("No upcoming sessions scheduled.")

    # ==========================
    # HOMEWORK
    # ==========================
    elif option == "Homework":
        from modules.homework import student_homework
        student_homework()

    # ==========================
    # SCHEDULE
    # ==========================
    elif option == "Schedule":
        st.title("My Sessions")
        sessions = query_dataframe("SELECT session_date, session_time, topic, notes FROM sessions WHERE student_id=? ORDER BY session_date", (student_id,))
        st.dataframe(sessions, use_container_width=True)

        zoom = query_dataframe("SELECT zoom_link, meeting_id FROM students WHERE id=?", (student_id,))
        if len(zoom) > 0:
            st.info(f"Zoom Link: {zoom.iloc[0]['zoom_link']}\n\nMeeting ID: {zoom.iloc[0]['meeting_id']}")

    # ==========================
    # PAYMENTS
    # ==========================
    elif option == "Payments":
        st.title("Payment History")
        payments = query_dataframe("SELECT amount, payment_date, period FROM payments WHERE student_id=? ORDER BY payment_date DESC", (student_id,))
        st.dataframe(payments, use_container_width=True)
