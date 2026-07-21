from datetime import date, timedelta
import pandas as pd
import streamlit as st

from database import execute, query_dataframe


def ensure_attendance_schema():
    """Ensure attendance table exists in PostgreSQL / SQLite."""
    try:
        execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                session_date DATE NOT NULL,
                session_time TIME NOT NULL,
                status TEXT NOT NULL,
                marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    except Exception:
        pass


def attendance_management():
    st.header("📋 Attendance Management & History")
    st.caption("Track, record, and export student attendance logs across tutoring sessions.")

    # Run auto-migration check
    ensure_attendance_schema()

    tab_history, tab_record = st.tabs(["📊 Attendance History & Analytics", "✏️ Record / Edit Attendance"])

    # ==========================================
    # TAB 1: ATTENDANCE HISTORY & ANALYTICS
    # ==========================================
    with tab_history:
        # Filter Sidebar/Columns
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

        with col_f1:
            students = query_dataframe(
                """
                SELECT id, first_name || ' ' || last_name AS student_name
                FROM students
                ORDER BY last_name, first_name
                """
            )
            student_options = {"All Students": None}
            if not students.empty:
                for _, row in students.iterrows():
                    student_options[f"{row['student_name']} (ID: {row['id']})"] = row['id']

            selected_student_label = st.selectbox("Filter by Student", list(student_options.keys()))
            selected_student_id = student_options[selected_student_label]

        with col_f2:
            date_range = st.date_input(
                "Filter Date Range",
                value=(date.today() - timedelta(days=30), date.today())
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = date.today() - timedelta(days=30), date.today()

        with col_f3:
            status_filter = st.selectbox(
                "Filter Status",
                ["All Statuses", "Present", "Late", "Absent - Excused", "Absent - Unexcused"]
            )

        # Build Dynamic Query (using PostgreSQL %s syntax)
        query = """
            SELECT
                a.id AS record_id,
                s.first_name || ' ' || s.last_name AS student,
                a.session_date::text AS session_date,
                a.session_time::text AS session_time,
                a.status AS status,
                a.marked_at::text AS recorded_at
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.session_date BETWEEN %s AND %s
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if selected_student_id:
            query += " AND a.student_id = %s"
            params.append(selected_student_id)

        if status_filter != "All Statuses":
            query += " AND a.status = %s"
            params.append(status_filter)

        query += " ORDER BY a.session_date DESC, a.session_time DESC"

        history = query_dataframe(query, tuple(params))

        # Metrics Overview
        if not history.empty:
            # Case-safe column lookup
            status_col = "status" if "status" in history.columns else history.columns[3]
            
            total_sessions = len(history)
            presents = len(history[history[status_col].isin(["Present", "Late"])])
            unexcused = len(history[history[status_col] == "Absent - Unexcused"])
            lates = len(history[history[status_col] == "Late"])

            pct_present = round((presents / total_sessions) * 100, 1) if total_sessions > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Logged Sessions", total_sessions)
            m2.metric("Attendance Rate", f"{pct_present}%")
            m3.metric("Late Arrivals", lates)
            m4.metric("Unexcused Absences", unexcused)

            st.divider()

            # Format Display Table Columns
            display_df = history.rename(
                columns={
                    "student": "Student",
                    "session_date": "Date",
                    "session_time": "Time",
                    "status": "Status",
                    "recorded_at": "Recorded At"
                }
            )

            if "record_id" in display_df.columns:
                display_df = display_df.drop(columns=["record_id"])

            # Data Table
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # Export Button
            csv_data = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Attendance CSV",
                data=csv_data,
                file_name=f"attendance_report_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.info("No attendance logs found matching the selected filters.")

    # ==========================================
    # TAB 2: RECORD / EDIT ATTENDANCE
    # ==========================================
    with tab_record:
        st.subheader("Mark Session Attendance")

        if students.empty:
            st.warning("No students available. Please add students first.")
            return

        with st.form("mark_attendance_form", clear_on_submit=False):
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                student_label = st.selectbox(
                    "Select Student",
                    options=[label for label in student_options.keys() if label != "All Students"]
                )
                student_id = student_options[student_label]

                status = st.selectbox(
                    "Attendance Status",
                    ["Present", "Late", "Absent - Excused", "Absent - Unexcused"]
                )

            with col_s2:
                session_date = st.date_input("Session Date", value=date.today())
                session_time = st.time_input("Session Start Time")

            submit_attendance = st.form_submit_button("💾 Save Attendance Record", type="primary")

            if submit_attendance:
                # Check for existing record to prevent duplicates for the same student, date, and time
                existing = query_dataframe(
                    """
                    SELECT id FROM attendance
                    WHERE student_id = %s AND session_date = %s AND session_time = %s
                    """,
                    (student_id, session_date.isoformat(), session_time.strftime("%H:%M:%S"))
                )

                if not existing.empty:
                    # Update existing record
                    execute(
                        """
                        UPDATE attendance
                        SET status = %s, marked_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (status, int(existing.iloc[0]["id"]))
                    )
                    st.success("Existing attendance record updated successfully!")
                else:
                    # Insert new record
                    execute(
                        """
                        INSERT INTO attendance (student_id, session_date, session_time, status)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (student_id, session_date.isoformat(), session_time.strftime("%H:%M:%S"), status)
                    )
                    st.success("New attendance record saved successfully!")

                st.rerun()
