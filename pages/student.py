import streamlit as st
from utils.datetime_utils import today_str
from database import execute, query_dataframe


def ensure_student_portal_schema():
    """Safely ensure required columns exist in Postgres without breaking open transactions."""
    columns_to_ensure = {
        "students": [
            ("first_name", "TEXT"),
            ("last_name", "TEXT"),
            ("grade", "TEXT"),
            ("subject", "TEXT"),
            ("zoom_link", "TEXT"),
            ("meeting_id", "TEXT"),
        ],
        "homework": [
            ("archived", "INTEGER DEFAULT 0"),
            ("status", "TEXT DEFAULT 'Assigned'"),
        ],
        "payments": [
            ("period", "TEXT"),
            ("payment_date", "DATE DEFAULT CURRENT_DATE"),
            ("amount", "NUMERIC DEFAULT 0.00"),
        ],
    }

    for table_name, cols in columns_to_ensure.items():
        for col_name, col_type in cols:
            try:
                execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
                )
            except Exception:
                pass


def student_page():
    # Make sure database schema is synchronized
    ensure_student_portal_schema()

    user = st.session_state.get("user", {})
    student_id = user.get("student_id")

    if not student_id:
        st.error("No student profile found in session. Please log in again.")
        return

    st.sidebar.title("Student Portal")
    option = st.sidebar.radio("Menu", ["Dashboard", "Homework", "Schedule", "Payments"])

    # ==========================
    # DASHBOARD
    # ==========================
    if option == "Dashboard":
        st.title("Student Dashboard")

        # Query student details with fallback for potential missing columns
        student = query_dataframe(
            """
            SELECT 
                id,
                COALESCE(first_name, '') AS first_name,
                COALESCE(last_name, '') AS last_name,
                COALESCE(grade, 'N/A') AS grade,
                COALESCE(subject, 'N/A') AS subject 
            FROM students 
            WHERE id = %s
            """,
            (student_id,)
        )

        if not student.empty:
            row = student.iloc[0]
            st.success(
                f"Welcome {row['first_name']} {row['last_name']} | "
                f"Grade: {row['grade']} | Subject: {row['subject']}"
            )

            # Fetch KPIs
            homework_due = query_dataframe(
                """
                SELECT COUNT(*) AS total 
                FROM homework 
                WHERE student_id = %s 
                  AND COALESCE(status, 'Assigned') = 'Assigned' 
                  AND COALESCE(archived, 0) = 0
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
                (student_id, today_str())
            )

            payments = query_dataframe(
                """
                SELECT COALESCE(SUM(amount), 0) AS total 
                FROM payments 
                WHERE student_id = %s
                """,
                (student_id,)
            )

            # Fetch Single Next Session
            next_session = query_dataframe(
                """
                SELECT session_date, session_time, topic 
                FROM sessions 
                WHERE student_id = %s AND session_date >= %s 
                ORDER BY session_date ASC, session_time ASC 
                LIMIT 1
                """,
                (student_id, today_str())
            )

            hw_total = int(homework_due.iloc[0]["total"]) if not homework_due.empty else 0
            sess_total = int(sessions_count.iloc[0]["total"]) if not sessions_count.empty else 0
            pay_total = float(payments.iloc[0]["total"]) if not payments.empty else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric("📚 Homework Due", hw_total)
            c2.metric("📅 Total Upcoming", sess_total)
            c3.metric("💰 Payments Made", f"${pay_total:,.2f}")

            st.divider()
            st.subheader("Next Upcoming Session")
            if not next_session.empty:
                s = next_session.iloc[0]
                st.info(f"**Date:** {s['session_date']} at {s['session_time']} | **Topic:** {s['topic']}")
            else:
                st.write("No upcoming sessions scheduled.")
        else:
            st.warning(f"No student record found for Student ID: {student_id}")

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
        sessions = query_dataframe(
            """
            SELECT session_date, session_time, topic, notes 
            FROM sessions 
            WHERE student_id = %s 
            ORDER BY session_date ASC
            """,
            (student_id,)
        )
        st.dataframe(sessions, use_container_width=True)

        zoom = query_dataframe(
            """
            SELECT zoom_link, meeting_id 
            FROM students 
            WHERE id = %s
            """,
            (student_id,)
        )
        if not zoom.empty:
            z_link = zoom.iloc[0].get("zoom_link")
            m_id = zoom.iloc[0].get("meeting_id")
            if z_link or m_id:
                st.info(f"**Zoom Link:** {z_link or 'N/A'}\n\n**Meeting ID:** {m_id or 'N/A'}")

    # ==========================
    # PAYMENTS
    # ==========================
    elif option == "Payments":
        st.title("Payment History")
        payments = query_dataframe(
            """
            SELECT amount, payment_date, period 
            FROM payments 
            WHERE student_id = %s 
            ORDER BY payment_date DESC
            """,
            (student_id,)
        )
        st.dataframe(payments, use_container_width=True)
