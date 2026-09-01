from datetime import date, timedelta
import io

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from database import execute, query_dataframe


# ============================================================
# ATTENDANCE SCHEMA
# ============================================================

def ensure_attendance_schema():

    """
    Ensure the attendance table exists and has the
    unique session constraint required by the portal.

    A tutoring session is identified by:

        student_id
        session_date
        session_time

    This matches the scheduler and student profile.
    """

    try:

        execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (

                id SERIAL PRIMARY KEY,

                student_id INTEGER NOT NULL
                    REFERENCES students(id)
                    ON DELETE CASCADE,

                session_date DATE NOT NULL,

                session_time TIME NOT NULL,

                status TEXT NOT NULL,

                marked_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT attendance_session_unique
                    UNIQUE (
                        student_id,
                        session_date,
                        session_time
                    )
            );
            """
        )

    except Exception as e:

        # The table may already exist.
        # Try to add the unique constraint separately.
        try:

            execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                attendance_student_session_unique
                ON attendance (
                    student_id,
                    session_date,
                    session_time
                );
                """
            )

        except Exception:

            # Do not prevent the application from loading
            # if the database already contains an equivalent
            # constraint/index.
            pass


# ============================================================
# ATTENDANCE STATUS OPTIONS
# ============================================================

ATTENDANCE_STATUSES = [
    "Present",
    "Late",
    "Absent - Excused",
    "Absent - Unexcused"
]


# ============================================================
# NORMALIZE TIME
# ============================================================

def normalize_time(value):

    """
    Normalize database/session time values into HH:MM AM/PM.

    Handles values such as:

        09:00:00
        09:00:00.000000
        09:00 AM
        9:00 AM
    """

    if value is None:

        return ""

    text = str(value).strip()

    if not text:

        return ""

    # Remove microseconds
    if "." in text:

        text = text.split(".")[0]

    # Try database TIME format
    for fmt in [
        "%H:%M:%S",
        "%H:%M",
        "%I:%M %p",
        "%I:%M:%S %p"
    ]:

        try:

            parsed = pd.to_datetime(
                text,
                format=fmt
            )

            return parsed.strftime(
                "%I:%M %p"
            ).lstrip("0")

        except Exception:

            continue

    return text


# ============================================================
# ATTENDANCE MANAGEMENT
# ============================================================

def attendance_management():

    st.header(
        "📋 Attendance History & Analytics"
    )

    st.caption(
        "View and export student attendance logs "
        "across tutoring sessions."
    )

    # ========================================================
    # ENSURE DATABASE
    # ========================================================

    ensure_attendance_schema()

    # ========================================================
    # FILTERS
    # ========================================================

    col_f1, col_f2, col_f3 = st.columns(
        [2, 2, 2]
    )

    # ========================================================
    # STUDENT FILTER
    # ========================================================

    with col_f1:

        students = query_dataframe(
            """
            SELECT
                id,
                first_name,
                last_name

            FROM students

            ORDER BY
                last_name,
                first_name
            """
        )

        student_options = {
            "All Students": None
        }

        if not students.empty:

            for _, row in students.iterrows():

                first = (
                    str(row["first_name"])
                    if pd.notna(row["first_name"])
                    else ""
                )

                last = (
                    str(row["last_name"])
                    if pd.notna(row["last_name"])
                    else ""
                )

                name = (
                    f"{first} {last}"
                ).strip()

                student_options[
                    f"{name} (ID: {row['id']})"
                ] = int(row["id"])

        selected_student_label = st.selectbox(
            "Filter by Student",
            list(student_options.keys()),
            key="attendance_student_filter"
        )

        selected_student_id = student_options[
            selected_student_label
        ]

    # ========================================================
    # DATE FILTER
    # ========================================================

    with col_f2:

        date_range = st.date_input(
            "Filter Date Range",
            value=(
                date.today() - timedelta(days=30),
                date.today()
            ),
            key="attendance_date_filter"
        )

        if (
            isinstance(date_range, tuple)
            and len(date_range) == 2
        ):

            start_date, end_date = date_range

        elif (
            isinstance(date_range, list)
            and len(date_range) == 2
        ):

            start_date, end_date = date_range

        else:

            start_date = (
                date.today()
                - timedelta(days=30)
            )

            end_date = date.today()

    # ========================================================
    # STATUS FILTER
    # ========================================================

    with col_f3:

        status_filter = st.selectbox(
            "Filter Status",
            [
                "All Statuses"
            ] + ATTENDANCE_STATUSES,
            key="attendance_status_filter"
        )

    # ========================================================
    # BUILD QUERY
    # ========================================================

    query = """
        SELECT

            a.id AS record_id,

            a.student_id,

            s.first_name || ' ' || s.last_name
                AS student,

            a.session_date::text
                AS session_date,

            a.session_time::text
                AS session_time,

            COALESCE(
                se.topic,
                ''
            ) AS lesson_topic,

            a.status
                AS status,

            TO_CHAR(
                a.marked_at,
                'YYYY-MM-DD HH24:MI'
            ) AS recorded_at

        FROM attendance a

        JOIN students s
            ON a.student_id = s.id

        LEFT JOIN sessions se
            ON se.student_id = a.student_id
            AND se.session_date = a.session_date
            AND se.session_time = a.session_time

        WHERE
            a.session_date BETWEEN %s AND %s
    """

    params = [
        start_date.isoformat(),
        end_date.isoformat()
    ]

    # ========================================================
    # STUDENT FILTER
    # ========================================================

    if selected_student_id is not None:

        query += """
            AND a.student_id = %s
        """

        params.append(
            selected_student_id
        )

    # ========================================================
    # STATUS FILTER
    # ========================================================

    if status_filter != "All Statuses":

        query += """
            AND a.status = %s
        """

        params.append(
            status_filter
        )

    # ========================================================
    # ORDER
    # ========================================================

    query += """
        ORDER BY
            a.session_date DESC,
            a.session_time DESC
    """

    # ========================================================
    # LOAD DATA
    # ========================================================

    history = query_dataframe(
        query,
        tuple(params)
    )

    # ========================================================
    # NO RESULTS
    # ========================================================

    if history.empty:

        st.info(
            "No attendance logs found matching "
            "the selected filters."
        )

        return

    # ========================================================
    # NORMALIZE TIME FOR DISPLAY
    # ========================================================

    history["session_time"] = (
        history["session_time"]
        .apply(normalize_time)
    )

    # ========================================================
    # ATTENDANCE METRICS
    # ========================================================

    total_sessions = len(history)

    presents = len(
        history[
            history["status"].isin(
                [
                    "Present",
                    "Late"
                ]
            )
        ]
    )

    lates = len(
        history[
            history["status"] == "Late"
        ]
    )

    unexcused = len(
        history[
            history["status"]
            == "Absent - Unexcused"
        ]
    )

    excused = len(
        history[
            history["status"]
            == "Absent - Excused"
        ]
    )

    pct_present = (

        round(
            (presents / total_sessions) * 100,
            1
        )

        if total_sessions > 0

        else 0
    )

    # ========================================================
    # KPI DISPLAY
    # ========================================================

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Total Logged Sessions",
        total_sessions
    )

    m2.metric(
        "Attendance Rate",
        f"{pct_present}%"
    )

    m3.metric(
        "Late Arrivals",
        lates
    )

    m4.metric(
        "Unexcused Absences",
        unexcused
    )

    # ========================================================
    # ADDITIONAL SUMMARY
    # ========================================================

    with st.expander(
        "📊 Attendance Summary"
    ):

        summary_col1, summary_col2 = st.columns(2)

        summary_col1.write(
            f"**Present:** {len(history[history['status'] == 'Present'])}"
        )

        summary_col1.write(
            f"**Late:** {lates}"
        )

        summary_col2.write(
            f"**Excused Absence:** {excused}"
        )

        summary_col2.write(
            f"**Unexcused Absence:** {unexcused}"
        )

    st.divider()

    # ========================================================
    # DISPLAY TABLE
    # ========================================================

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

    columns_to_keep = [
        "Student",
        "Date",
        "Time",
        "Lesson Topic",
        "Status",
        "Recorded At"
    ]

    display_df = display_df[
        [
            col
            for col in columns_to_keep
            if col in display_df.columns
        ]
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Student": "👨‍🎓 Student",
            "Date": "📅 Date",
            "Time": "⏰ Time",
            "Lesson Topic": "📖 Lesson Topic",
            "Status": "✅ Status",
            "Recorded At": "🕒 Recorded At"
        }
    )

    # ========================================================
    # EXPORT
    # ========================================================

    st.subheader(
        "⬇️ Export Attendance"
    )

    # ========================================================
    # CSV EXPORT
    # ========================================================

    csv_data = display_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📊 Export Attendance CSV",
        data=csv_data,
        file_name=(
            f"attendance_"
            f"{start_date}_"
            f"{end_date}.csv"
        ),
        mime="text/csv",
        key="attendance_csv_download"
    )

    # ========================================================
    # PDF EXPORT
    # ========================================================

    pdf_buffer = io.BytesIO()

    try:

        # ----------------------------------------------------
        # DOCUMENT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        elements.append(
            Paragraph(
                "Attendance Report",
                styles["Title"]
            )
        )

        elements.append(
            Spacer(1, 8)
        )

        # ----------------------------------------------------
        # REPORT INFORMATION
        # ----------------------------------------------------

        elements.append(
            Paragraph(
                (
                    f"<b>Date Range:</b> "
                    f"{start_date} to {end_date}"
                ),
                styles["Normal"]
            )
        )

        if selected_student_id is not None:

            student_text = (
                f"<b>Student:</b> "
                f"{selected_student_label}"
            )

        else:

            student_text = (
                "<b>Student:</b> All Students"
            )

        elements.append(
            Paragraph(
                student_text,
                styles["Normal"]
            )
        )

        elements.append(
            Paragraph(
                (
                    f"<b>Status Filter:</b> "
                    f"{status_filter}"
                ),
                styles["Normal"]
            )
        )

        elements.append(
            Spacer(1, 12)
        )

        # ----------------------------------------------------
        # SUMMARY TABLE
        # ----------------------------------------------------

        summary_data = [

            [
                "Total Sessions",
                "Attendance Rate",
                "Late Arrivals",
                "Excused Absences",
                "Unexcused Absences"
            ],

            [
                str(total_sessions),
                f"{pct_present}%",
                str(lates),
                str(excused),
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
                        8
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

        # ----------------------------------------------------
        # PDF ATTENDANCE TABLE
        # ----------------------------------------------------

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
                    ),

                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.whitesmoke
                        ]
                    )
                ]
            )
        )

        elements.append(
            attendance_table
        )

        # ----------------------------------------------------
        # BUILD
        # ----------------------------------------------------

        doc.build(
            elements
        )

        pdf_buffer.seek(0)

        pdf_bytes = pdf_buffer.getvalue()

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        st.download_button(
            label="📄 Export Attendance PDF",
            data=pdf_bytes,
            file_name=(
                f"attendance_report_"
                f"{start_date}_"
                f"{end_date}.pdf"
            ),
            mime="application/pdf",
            key="attendance_pdf_download"
        )

    except Exception as e:

        st.error(
            f"Unable to create PDF: {e}"
        )
