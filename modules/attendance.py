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
    st.header("📋 Attendance History & Analytics")
    st.caption("View and export student attendance logs across tutoring sessions.")

    # Run auto-migration check
    ensure_attendance_schema()

    # Filter Sidebar / Top Columns
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

    with col_f1:
        # Uses cached query_dataframe safely
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
            COALESCE(se.topic, '') AS lesson_topic,
            a.status AS status,
            TO_CHAR(a.marked_at, 'YYYY-MM-DD HH24:MI') AS recorded_at
        FROM attendance a
        JOIN students s
            ON a.student_id = s.id
    
        LEFT JOIN sessions se
            ON se.student_id = a.student_id
            AND se.session_date = a.session_date
            AND se.session_time = a.session_time
    
        WHERE a.session_date BETWEEN %s AND %s
    """
    
    params = [
        start_date.isoformat(),
        end_date.isoformat()
    ]
    
    
    if selected_student_id:
    
        query += """
            AND a.student_id = %s
        """
    
        params.append(
            selected_student_id
        )
    
    
    if status_filter != "All Statuses":
    
        query += """
            AND a.status = %s
        """
    
        params.append(
            status_filter
        )
    
    
    query += """
        ORDER BY
            a.session_date DESC,
            a.session_time DESC
    """

    # Fetches filtered attendance history via cache layer
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
                "lesson_topic": "Lesson Topic",
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

        # ========================================================
        # EXPORT ATTENDANCE
        # ========================================================
        
        st.subheader("⬇️ Export Attendance")
        
        col_export1, col_export2 = st.columns(2)
        
        
        # ========================================================
        # CSV EXPORT
        # ========================================================
        
        with col_export1:
        
            csv_data = display_df.to_csv(
                index=False
            ).encode("utf-8")
        
            st.download_button(
                "📥 Export Attendance CSV",
                data=csv_data,
                file_name=(
                    f"attendance_report_"
                    f"{start_date}_{end_date}.csv"
                ),
                mime="text/csv",
                use_container_width=True,
                key="attendance_csv_download"
            )
        
        
        # ========================================================
        # PDF EXPORT
        # ========================================================
        
        with col_export2:
        
            try:
        
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import landscape, letter
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Table,
                    TableStyle,
                    Paragraph,
                    Spacer
                )
                from reportlab.lib.styles import getSampleStyleSheet
        
                pdf_buffer = __import__("io").BytesIO()
        
                doc = SimpleDocTemplate(
                    pdf_buffer,
                    pagesize=landscape(letter),
                    rightMargin=25,
                    leftMargin=25,
                    topMargin=25,
                    bottomMargin=25
                )
        
                styles = getSampleStyleSheet()
        
                elements = []
        
                # ------------------------------------------------
                # TITLE
                # ------------------------------------------------
        
                elements.append(
                    Paragraph(
                        "Attendance Report",
                        styles["Title"]
                    )
                )
        
                elements.append(
                    Paragraph(
                        f"Date Range: {start_date} to {end_date}",
                        styles["Normal"]
                    )
                )
        
                if selected_student_id:
        
                    elements.append(
                        Paragraph(
                            f"Student: {selected_student_label}",
                            styles["Normal"]
                        )
                    )
        
                else:
        
                    elements.append(
                        Paragraph(
                            "Student: All Students",
                            styles["Normal"]
                        )
                    )
        
                elements.append(
                    Paragraph(
                        f"Status Filter: {status_filter}",
                        styles["Normal"]
                    )
                )
        
                elements.append(
                    Spacer(1, 12)
                )
        
                # ------------------------------------------------
                # SUMMARY
                # ------------------------------------------------
        
                summary_data = [
                    [
                        "Total Sessions",
                        "Attendance Rate",
                        "Late Arrivals",
                        "Unexcused Absences"
                    ],
                    [
                        str(total_sessions),
                        f"{pct_present}%",
                        str(lates),
                        str(unexcused)
                    ]
                ]
        
                summary_table = Table(
                    summary_data
                )
        
                summary_table.setStyle(
                    TableStyle(
                        [
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, 0),
                                colors.grey
                            ),
                            (
                                "TEXTCOLOR",
                                (0, 0),
                                (-1, 0),
                                colors.white
                            ),
                            (
                                "FONTNAME",
                                (0, 0),
                                (-1, 0),
                                "Helvetica-Bold"
                            ),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.5,
                                colors.grey
                            ),
                            (
                                "ALIGN",
                                (0, 0),
                                (-1, -1),
                                "CENTER"
                            ),
                            (
                                "FONTSIZE",
                                (0, 0),
                                (-1, -1),
                                9
                            )
                        ]
                    )
                )
        
                elements.append(
                    summary_table
                )
        
                elements.append(
                    Spacer(1, 15)
                )
        
                # ------------------------------------------------
                # ATTENDANCE TABLE
                # ------------------------------------------------
        
                pdf_df = display_df.copy()
        
                pdf_df = pdf_df.fillna("")
        
                pdf_data = [
                    list(pdf_df.columns)
                ]
        
                for _, row in pdf_df.iterrows():
        
                    pdf_data.append(
                        [
                            str(value)
                            for value in row.tolist()
                        ]
                    )
        
                attendance_table = Table(
                    pdf_data,
                    repeatRows=1
                )
        
                attendance_table.setStyle(
                    TableStyle(
                        [
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, 0),
                                colors.grey
                            ),
                            (
                                "TEXTCOLOR",
                                (0, 0),
                                (-1, 0),
                                colors.white
                            ),
                            (
                                "FONTNAME",
                                (0, 0),
                                (-1, 0),
                                "Helvetica-Bold"
                            ),
                            (
                                "GRID",
                                (0, 0),
                                (-1, -1),
                                0.4,
                                colors.grey
                            ),
                            (
                                "FONTSIZE",
                                (0, 0),
                                (-1, -1),
                                7
                            ),
                            (
                                "VALIGN",
                                (0, 0),
                                (-1, -1),
                                "TOP"
                            )
                        ]
                    )
                )
        
                elements.append(
                    attendance_table
                )
        
                # ------------------------------------------------
                # BUILD PDF
                # ------------------------------------------------
        
                doc.build(
                    elements
                )
        
                pdf_buffer.seek(0)
        
                st.download_button(
                    "📄 Export Attendance PDF",
                    data=pdf_buffer.getvalue(),
                    file_name=(
                        f"attendance_report_"
                        f"{start_date}_{end_date}.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
                    key="attendance_pdf_download"
                )
        
            except Exception as e:
        
                st.error(
                    f"Unable to create PDF: {e}"
                )
    else:
        st.info("No attendance logs found matching the selected filters.")
