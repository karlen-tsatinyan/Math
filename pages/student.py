import streamlit as st
from utils.datetime_utils import today_str
from database import execute, query_dataframe


def get_existing_columns(table_name):
    """Retrieve existing column names for a given table in PostgreSQL."""
    try:
        df = query_dataframe(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
            """,
            (table_name,)
        )
        if not df.empty:
            return set(df["column_name"].str.lower().tolist())
    except Exception:
        pass
    return set()


def ensure_student_portal_schema():
    """Safely ensure essential columns exist in PostgreSQL."""
    columns_to_add = [
        ("students", "first_name", "TEXT DEFAULT ''"),
        ("students", "last_name", "TEXT DEFAULT ''"),
        ("students", "grade", "TEXT DEFAULT 'N/A'"),
        ("students", "subject", "TEXT DEFAULT 'N/A'"),
        ("students", "zoom_link", "TEXT"),
        ("students", "meeting_id", "TEXT"),
        ("homework", "archived", "INTEGER DEFAULT 0"),
        ("homework", "status", "TEXT DEFAULT 'Assigned'"),
        ("payments", "period", "TEXT"),
        ("payments", "payment_date", "DATE DEFAULT CURRENT_DATE"),
        ("payments", "amount", "NUMERIC DEFAULT 0.00"),
    ]

    for table_name, col_name, col_type in columns_to_add:
        try:
            execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
        except Exception:
            pass


def student_page():
    # Make sure missing columns are added automatically
    ensure_student_portal_schema()

    user = st.session_state.get("user", {})
    raw_student_id = user.get("student_id") or user.get("id")

    if not raw_student_id:
        st.error("No student profile found in session. Please log in again.")
        return

    # Force student_id to an integer to prevent psycopg2 type mismatches
    try:
        student_id = int(raw_student_id)
    except (ValueError, TypeError):
        st.error("Invalid student profile ID format.")
        return

    st.sidebar.title("Student Portal")
    option = st.sidebar.radio("Menu", ["Dashboard", "Homework", "Schedule", "Payments"])

    # Fetch actual existing columns in students table
    student_cols = get_existing_columns("students")

    # ==========================
    # DASHBOARD
    # ==========================
    if option == "Dashboard":
        st.title("Student Dashboard")

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

            # Check homework columns
            hw_cols = get_existing_columns("homework")
            hw_status_clause = "AND status = 'Assigned'" if "status" in hw_cols else ""
            hw_arch_clause = "AND archived = 0" if "archived" in hw_cols else ""

            # Fetch KPIs
            homework_due = query_dataframe(
                f"""
                SELECT COUNT(*) AS total 
                FROM homework 
                WHERE student_id = %s {hw_status_clause} {hw_arch_clause}
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
        pay_cols = get_existing_columns("payments")
        period_col = "period" if "period" in pay_cols else "'' AS period"

        payments = query_dataframe(
            f"""
            SELECT amount, payment_date, {period_col} 
            FROM payments 
            WHERE student_id = %s 
            ORDER BY payment_date DESC
            """,
            (student_id,)
        )
        st.dataframe(payments, use_container_width=True)
