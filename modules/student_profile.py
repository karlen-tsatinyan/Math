import streamlit as st
import pandas as pd

from datetime import datetime, date, time

from database import query_dataframe, execute
from utils.datetime_utils import today_str

from modules.performance import student_performance_view


# ============================================================
# CACHE SETTINGS
# ============================================================

CACHE_TTL = 300


# ============================================================
# GENERAL HELPERS
# ============================================================

def clear_student_profile_cache():
    """
    Clear cached database queries after a student/session/
    attendance/payment update.
    """

    st.cache_data.clear()

    if hasattr(st, "cache_resource"):
        st.cache_resource.clear()


def clean_value(value, default=""):
    """
    Safely convert database values into displayable strings.
    """

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except Exception:
        pass

    text = str(value).strip()

    if text.lower() in ["nan", "none", "nat"]:
        return default

    return text


def format_date_value(value):
    """
    Convert database date values into YYYY-MM-DD.
    """

    if value is None:
        return ""

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce"
        )

        if pd.isna(parsed):
            return clean_value(value)

        return parsed.strftime("%Y-%m-%d")

    except Exception:

        return clean_value(value)


def parse_session_datetime(session_date, session_time):
    """
    Safely combine database session date/time values.

    Supports common PostgreSQL / SQLite formats.
    """

    if session_date is None or session_time is None:
        return None

    date_text = clean_value(session_date)
    time_text = clean_value(session_time)

    if not date_text or not time_text:
        return None

    # --------------------------------------------------------
    # Try pandas first
    # --------------------------------------------------------

    try:

        result = pd.to_datetime(
            f"{date_text} {time_text}",
            errors="coerce"
        )

        if not pd.isna(result):

            return result.to_pydatetime()

    except Exception:
        pass

    # --------------------------------------------------------
    # Explicit formats
    # --------------------------------------------------------

    formats = [
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M",
    ]

    combined = f"{date_text} {time_text}"

    for fmt in formats:

        try:

            return datetime.strptime(
                combined,
                fmt
            )

        except Exception:
            continue

    return None


def format_time_value(value):
    """
    Display session times consistently.
    """

    if value is None:
        return ""

    text = clean_value(value)

    if not text:
        return ""

    # Already likely formatted correctly
    if "AM" in text.upper() or "PM" in text.upper():

        try:

            parsed = datetime.strptime(
                text.upper(),
                "%I:%M %p"
            )

            return parsed.strftime(
                "%I:%M %p"
            )

        except Exception:

            return text

    # 24-hour format
    for fmt in [
        "%H:%M",
        "%H:%M:%S"
    ]:

        try:

            parsed = datetime.strptime(
                text,
                fmt
            )

            return parsed.strftime(
                "%I:%M %p"
            )

        except Exception:
            continue

    return text


def format_duration(value):
    """
    Format scheduler duration.

    The scheduler normally stores duration as minutes.
    """

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except Exception:
        pass

    try:

        minutes = int(value)

        if minutes <= 0:
            return ""

        if minutes < 60:

            return f"{minutes} min"

        hours = minutes // 60
        remaining = minutes % 60

        if remaining == 0:

            return (
                f"{hours} hr"
                if hours == 1
                else f"{hours} hrs"
            )

        return (
            f"{hours} hr {remaining} min"
            if hours == 1
            else f"{hours} hrs {remaining} min"
        )

    except Exception:

        return clean_value(value)


# ============================================================
# LOAD STUDENTS
# ============================================================

@st.cache_data(
    ttl=CACHE_TTL,
    show_spinner=False
)
def get_students():

    return query_dataframe(
        """
        SELECT
            id,
            COALESCE(first_name, '') AS first_name,
            COALESCE(last_name, '') AS last_name,
            COALESCE(grade, '') AS grade,
            COALESCE(subject, '') AS subject,
            email,
            phone,
            zoom_link,
            meeting_id,
            COALESCE(archived, 0) AS archived
        FROM students
        WHERE COALESCE(archived, 0) = 0
        ORDER BY
            last_name,
            first_name
        """
    )


# ============================================================
# STUDENT OVERVIEW
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_student_overview(student_id):

    return query_dataframe(
        """
        SELECT

            (
                SELECT COALESCE(
                    SUM(amount),
                    0
                )
                FROM payments
                WHERE student_id = %s
            ) AS payment_total,

            (
                SELECT COUNT(*)
                FROM sessions
                WHERE student_id = %s
            ) AS session_total,

            (
                SELECT COUNT(*)
                FROM attendance
                WHERE student_id = %s
                  AND status = 'Present'
            ) AS attendance_total,

            (
                SELECT COUNT(*)
                FROM homework
                WHERE student_id = %s
            ) AS homework_total

        """,
        (
            student_id,
            student_id,
            student_id,
            student_id
        )
    )


# ============================================================
# NEXT SESSION
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_next_session(
    student_id,
    current_date
):

    return query_dataframe(
        """
        SELECT
            session_date,
            session_time,
            topic,
            duration,
            status
        FROM sessions
        WHERE student_id = %s
          AND session_date >= %s
          AND COALESCE(status, 'Scheduled')
              NOT IN ('Cancelled', 'Canceled')
        ORDER BY
            session_date ASC,
            session_time ASC
        LIMIT 1
        """,
        (
            student_id,
            current_date
        )
    )


# ============================================================
# LATEST HOMEWORK GRADE
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_latest_grade(student_id):

    return query_dataframe(
        """
        SELECT
            assignment,
            percentage,
            grade,
            grade_date,
            teacher_comment
        FROM homework_grades
        WHERE student_id = %s
          AND assignment IS NOT NULL
          AND percentage IS NOT NULL
          AND grade_date IS NOT NULL
        ORDER BY
            grade_date DESC
        LIMIT 1
        """,
        (
            student_id,
        )
    )


# ============================================================
# PAYMENT HISTORY
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_payment_history(student_id):

    return query_dataframe(
        """
        SELECT
            amount AS "Amount",
            payment_date AS "Payment Date",
            period AS "Period",
            status AS "Status"
        FROM payments
        WHERE student_id = %s
        ORDER BY
            payment_date DESC
        """,
        (
            student_id,
        )
    )


# ============================================================
# HOMEWORK HISTORY
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_homework_history(student_id):

    return query_dataframe(
        """
        SELECT
            title AS "Homework",
            curriculum_topic AS "Curriculum Topic",
            status AS "Status",
            grade AS "Grade",
            teacher_feedback AS "Teacher Feedback",
            created_at AS "Assigned",
            due_date AS "Due Date",
            reviewed_at AS "Graded On"
        FROM homework
        WHERE student_id = %s
        ORDER BY
            created_at DESC
        """,
        (
            student_id,
        )
    )


# ============================================================
# SESSION + ATTENDANCE
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)

def get_sessions_with_attendance(student_id):

    return query_dataframe(
        """
        SELECT

            s.id AS session_id,

            s.session_date::text AS session_date,

            s.session_time::text AS session_time,

            COALESCE(
                s.topic,
                ''
            ) AS topic,

            COALESCE(
                s.notes,
                ''
            ) AS notes,

            CASE
                WHEN a.id IS NOT NULL
                     AND a.status = 'Present'
                THEN 1
                ELSE 0
            END AS attendance_marked,

            COALESCE(
                a.status,
                'Pending'
            ) AS attendance_status

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
        (
            student_id,
        )
    )


# ============================================================
# ATTENDANCE HISTORY
# ============================================================

@st.cache_data(
    ttl=120,
    show_spinner=False
)
def get_attendance_history(student_id):

    return query_dataframe(
        """
        SELECT

            a.session_date AS "Date",

            a.session_time AS "Time",

            COALESCE(
                s.topic,
                ''
            ) AS "Lesson Topic",

            a.status AS "Status",

            a.marked_at AS "Recorded At"

        FROM attendance a

        LEFT JOIN sessions s
            ON s.student_id =
                a.student_id

            AND s.session_date =
                a.session_date

            AND s.session_time =
                a.session_time

        WHERE a.student_id = %s

        ORDER BY
            a.session_date DESC,
            a.session_time DESC
        """,
        (
            student_id,
        )
    )


# ============================================================
# ATTENDANCE UPDATE
# ============================================================

def mark_attendance(
    student_id,
    session_date,
    session_time
):

    execute(
        """
        INSERT INTO attendance
        (
            student_id,
            session_date,
            session_time,
            status
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        ON CONFLICT
        (
            student_id,
            session_date,
            session_time
        )
        DO UPDATE SET
            status = EXCLUDED.status
        """,
        (
            int(student_id),
            session_date,
            session_time,
            "Present"
        )
    )


def remove_attendance(
    student_id,
    session_date,
    session_time
):

    execute(
        """
        DELETE FROM attendance
        WHERE student_id = %s
          AND session_date = %s
          AND session_time = %s
        """,
        (
            int(student_id),
            session_date,
            session_time
        )
    )


# ============================================================
# STUDENT PROFILE
# ============================================================

def student_profile():

    st.title(
        "👨‍🎓 Student Profile"
    )

    # ========================================================
    # LOAD STUDENTS
    # ========================================================

    students = get_students()

    if students.empty:

        st.warning(
            "No active students found."
        )

        return

    # ========================================================
    # CREATE DISPLAY NAME
    # ========================================================

    students = students.copy()

    students["name"] = (

        students["first_name"]
        .fillna("")
        .astype(str)
        .str.strip()

        + " "

        + students["last_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    ).str.strip()

    # ========================================================
    # STUDENT SELECTOR
    # ========================================================

    student_options = students["id"].tolist()

    selected_id = st.selectbox(
        "Select Student",
        student_options,
        format_func=lambda x: (
            f"{students.loc[students['id'] == x, 'name'].iloc[0]}"
            f"  (ID: {x})"
        ),
        key="student_profile_selector"
    )

    selected_rows = students[
        students["id"] == selected_id
    ]

    if selected_rows.empty:

        st.error(
            "Unable to find the selected student."
        )

        return

    student = selected_rows.iloc[0]

    student_id = int(
        student["id"]
    )

    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    st.subheader(
        "Student Information"
    )

    info_col1, info_col2, info_col3, info_col4, info_col5 = (
        st.columns(5)
    )

    with info_col1:

        st.caption("Name")

        st.write(
            clean_value(
                student["name"]
            )
        )

    with info_col2:

        st.caption("Grade")

        st.write(
            clean_value(
                student["grade"],
                "N/A"
            )
        )

    with info_col3:

        st.caption("Courses")

        st.write(
            clean_value(
                student["subject"],
                "N/A"
            )
        )

    with info_col4:

        st.caption("Email")

        st.write(
            clean_value(
                student["email"],
                "—"
            )
        )

    with info_col5:

        st.caption("Phone")

        st.write(
            clean_value(
                student["phone"],
                "—"
            )
        )

    # ========================================================
    # CLASSROOM INFORMATION
    # ========================================================

    zoom_link = clean_value(
        student["zoom_link"]
    )

    meeting_id = clean_value(
        student["meeting_id"]
    )

    if zoom_link or meeting_id:

        st.markdown(
            "### 💻 Classroom Information"
        )

        classroom_col1, classroom_col2 = st.columns(2)

        with classroom_col1:

            if zoom_link:

                st.markdown(
                    f"🔗 [Open General Zoom Room]({zoom_link})"
                )

            else:

                st.caption(
                    "No Zoom room assigned."
                )

        with classroom_col2:

            if meeting_id:

                st.write(
                    f"**Meeting ID:** {meeting_id}"
                )

    st.divider()

    # ========================================================
    # STUDENT OVERVIEW
    # ========================================================

    overview = get_student_overview(
        student_id
    )

    payment_total = 0
    session_total = 0
    attendance_total = 0
    homework_total = 0

    if not overview.empty:

        row = overview.iloc[0]

        try:
            payment_total = float(
                row["payment_total"] or 0
            )
        except Exception:
            payment_total = 0

        try:
            session_total = int(
                row["session_total"] or 0
            )
        except Exception:
            session_total = 0

        try:
            attendance_total = int(
                row["attendance_total"] or 0
            )
        except Exception:
            attendance_total = 0

        try:
            homework_total = int(
                row["homework_total"] or 0
            )
        except Exception:
            homework_total = 0

    # ========================================================
    # OVERVIEW METRICS
    # ========================================================

    st.subheader(
        "📊 Student Overview"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "💰 Payments",
        f"${payment_total:,.2f}"
    )

    col2.metric(
        "📅 Sessions",
        session_total
    )

    col3.metric(
        "✅ Attendance",
        attendance_total
    )

    col4.metric(
        "📚 Homework",
        homework_total
    )

    st.divider()

    # ========================================================
    # NEXT SESSION
    # ========================================================

    next_session = get_next_session(
        student_id,
        today_str()
    )

    if not next_session.empty:

        next_row = next_session.iloc[0]

        next_date = format_date_value(
            next_row["session_date"]
        )

        next_time = format_time_value(
            next_row["session_time"]
        )

        next_topic = clean_value(
            next_row["topic"],
            "No topic entered"
        )

        next_duration = format_duration(
            next_row.get("duration")
        )

        duration_text = ""

        if next_duration:

            duration_text = (
                f"  |  ⏱️ {next_duration}"
            )

        st.info(
            f"""
**📅 Next Lesson**

**Date:** {next_date}

**Time:** {next_time}{duration_text}

**Topic:** {next_topic}
"""
        )

    # ========================================================
    # LATEST HOMEWORK GRADE
    # ========================================================

    latest_grade = get_latest_grade(
        student_id
    )

    if not latest_grade.empty:

        latest = latest_grade.iloc[0]

        assignment = clean_value(
            latest["assignment"],
            "Homework"
        )

        percentage = clean_value(
            latest["percentage"]
        )

        grade_letter = clean_value(
            latest.get("grade"),
            ""
        )

        grade_date = format_date_value(
            latest["grade_date"]
        )

        grade_display = percentage

        if grade_letter:

            grade_display = (
                f"{grade_letter} — {percentage}%"
            )

        st.success(
            f"""
**📚 Latest Homework Grade**

**Assignment:** {assignment}

**Grade:** {grade_display}

**Date:** {grade_date}
"""
        )

    # ========================================================
    # MAIN TABS
    # ========================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "💰 Payments",
            "📚 Homework",
            "📅 Sessions",
            "✅ Attendance",
            "📈 Performance"
        ]
    )

    # ========================================================
    # TAB 1 — PAYMENTS
    # ========================================================

    with tab1:

        st.subheader(
            "💰 Payment History"
        )

        payments = get_payment_history(
            student_id
        )

        if payments.empty:

            st.info(
                "No payments."
            )

        else:

            payments = payments.copy()

            payments["Amount"] = pd.to_numeric(
                payments["Amount"],
                errors="coerce"
            ).fillna(0)

            payments["Amount"] = payments[
                "Amount"
            ].apply(
                lambda x: f"${x:,.2f}"
            )

            st.dataframe(
                payments,
                hide_index=True,
                use_container_width=True
            )

    # ========================================================
    # TAB 2 — HOMEWORK
    # ========================================================

    with tab2:

        st.subheader(
            "📚 Homework History"
        )

        homework = get_homework_history(
            student_id
        )

        if homework.empty:

            st.info(
                "No homework."
            )

        else:

            homework = homework.copy()

            if "Due Date" in homework.columns:

                homework["Due Date"] = homework[
                    "Due Date"
                ].apply(
                    format_date_value
                )

            if "Assigned" in homework.columns:

                homework["Assigned"] = pd.to_datetime(
                    homework["Assigned"],
                    errors="coerce"
                ).dt.strftime(
                    "%Y-%m-%d"
                )

            if "Graded On" in homework.columns:

                homework["Graded On"] = pd.to_datetime(
                    homework["Graded On"],
                    errors="coerce"
                ).dt.strftime(
                    "%Y-%m-%d"
                )

            st.dataframe(
                homework,
                hide_index=True,
                use_container_width=True
            )

    # ========================================================
    # TAB 3 — SESSIONS
    # ========================================================

    with tab3:

        st.subheader(
            "📅 Session History"
        )

        sessions = get_sessions_with_attendance(
            student_id
        )

        if sessions.empty:

            st.info(
                "No sessions."
            )

        else:

            sessions = sessions.copy()

            now = datetime.now()

            completed_rows = []
            upcoming_rows = []

            # =================================================
            # CLASSIFY SESSIONS
            # =================================================

            for _, row in sessions.iterrows():

                session_dt = parse_session_datetime(
                    row["session_date"],
                    row["session_time"]
                )

                session_status = clean_value(
                    row.get("session_status"),
                    "Scheduled"
                )

                if session_dt is None:

                    continue

                if session_status.lower() in [
                    "cancelled",
                    "canceled"
                ]:

                    # Keep cancelled sessions visible,
                    # but place them according to date.
                    pass

                session_data = {
                    "row": row,
                    "datetime": session_dt
                }

                if session_dt <= now:

                    completed_rows.append(
                        session_data
                    )

                else:

                    upcoming_rows.append(
                        session_data
                    )

            # =================================================
            # COMPLETED LESSONS
            # =================================================

            st.markdown(
                "### ✅ Completed Lessons"
            )

            if not completed_rows:

                st.info(
                    "No completed lessons yet."
                )

            else:

                # Newest completed first
                completed_rows.sort(
                    key=lambda x: x["datetime"],
                    reverse=True
                )

                for index, item in enumerate(
                    completed_rows
                ):

                    row = item["row"]

                    session_date = format_date_value(
                        row["session_date"]
                    )

                    session_time = format_time_value(
                        row["session_time"]
                    )

                    topic = clean_value(
                        row["topic"],
                        "No topic entered"
                    )

                    duration = format_duration(
                        row.get("duration")
                    )

                    session_status = clean_value(
                        row.get("session_status"),
                        "Scheduled"
                    )

                    attendance_marked = (
                        str(row["attendance_status"]).strip()
                        == "Present"
                    )

                    # -----------------------------------------
                    # SESSION CONTAINER
                    # -----------------------------------------

                    with st.container(
                        border=True
                    ):

                        top_col1, top_col2, top_col3 = (
                            st.columns(
                                [1.3, 1.2, 3]
                            )
                        )

                        with top_col1:

                            st.write(
                                f"📅 **{session_date}**"
                            )

                        with top_col2:

                            st.write(
                                f"⏰ **{session_time}**"
                            )

                        with top_col3:

                            st.write(
                                f"📖 **{topic}**"
                            )

                        detail_col1, detail_col2 = (
                            st.columns(2)
                        )

                        with detail_col1:

                            if duration:

                                st.caption(
                                    f"⏱️ Duration: {duration}"
                                )

                            if session_status:

                                st.caption(
                                    f"Status: {session_status}"
                                )

                        with detail_col2:

                            if clean_value(
                                row.get("repeat_type")
                            ):

                                repeat_text = clean_value(
                                    row.get("repeat_type")
                                )

                                st.caption(
                                    f"🔁 Repeat: {repeat_text}"
                                )

                        # -----------------------------------------
                        # ATTENDANCE CHECKBOX
                        # -----------------------------------------

                        checkbox_key = (
                            f"profile_attendance_"
                            f"{student_id}_"
                            f"{clean_value(row['session_date'])}_"
                            f"{clean_value(row['session_time'])}"
                        )

                        mark = st.checkbox(
                            "✅ Student attended",
                            value=attendance_marked,
                            key=checkbox_key
                        )

                        # -----------------------------------------
                        # UPDATE ATTENDANCE
                        # -----------------------------------------

                        if (
                            mark
                            and not attendance_marked
                        ):

                            try:

                                mark_attendance(
                                    student_id,
                                    row["session_date"],
                                    row["session_time"]
                                )

                                clear_student_profile_cache()

                                st.success(
                                    "Attendance marked as Present."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    f"Unable to mark attendance: {e}"
                                )

                        elif (
                            not mark
                            and attendance_marked
                        ):

                            try:

                                remove_attendance(
                                    student_id,
                                    row["session_date"],
                                    row["session_time"]
                                )

                                clear_student_profile_cache()

                                st.warning(
                                    "Attendance removed."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    f"Unable to remove attendance: {e}"
                                )

                        # -----------------------------------------
                        # NOTES
                        # -----------------------------------------

                        notes = clean_value(
                            row.get("notes")
                        )

                        if notes:

                            st.caption(
                                f"📝 Notes: {notes}"
                            )

            # =================================================
            # UPCOMING LESSONS
            # =================================================

            st.divider()

            st.markdown(
                "### 📅 Upcoming Lessons"
            )

            if not upcoming_rows:

                st.info(
                    "No upcoming lessons scheduled."
                )

            else:

                upcoming_rows.sort(
                    key=lambda x: x["datetime"]
                )

                upcoming_display = []

                for item in upcoming_rows:

                    row = item["row"]

                    session_status = clean_value(
                        row.get("session_status"),
                        "Scheduled"
                    )

                    topic = clean_value(
                        row.get("topic"),
                        "No topic entered"
                    )

                    duration = format_duration(
                        row.get("duration")
                    )

                    repeat_type = clean_value(
                        row.get("repeat_type")
                    )

                    upcoming_display.append(
                        {
                            "Date": format_date_value(
                                row["session_date"]
                            ),

                            "Time": format_time_value(
                                row["session_time"]
                            ),

                            "Topic": topic,

                            "Duration": duration
                            if duration
                            else "—",

                            "Repeat": repeat_type
                            if repeat_type
                            else "—",

                            "Status": session_status
                        }
                    )

                upcoming_df = pd.DataFrame(
                    upcoming_display
                )

                st.dataframe(
                    upcoming_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Date": "📅 Date",
                        "Time": "⏰ Time",
                        "Topic": "📖 Topic",
                        "Duration": "⏱️ Duration",
                        "Repeat": "🔁 Repeat",
                        "Status": "📌 Status"
                    }
                )

    # ========================================================
    # TAB 4 — ATTENDANCE
    # ========================================================

    with tab4:

        st.subheader(
            "✅ Attendance History & Analytics"
        )

        attendance = get_attendance_history(
            student_id
        )

        if attendance.empty:

            st.info(
                "No attendance records."
            )

        else:

            attendance = attendance.copy()

            if "Date" in attendance.columns:

                attendance["Date"] = attendance[
                    "Date"
                ].apply(
                    format_date_value
                )

            if "Time" in attendance.columns:

                attendance["Time"] = attendance[
                    "Time"
                ].apply(
                    format_time_value
                )

            if "Recorded At" in attendance.columns:

                attendance["Recorded At"] = pd.to_datetime(
                    attendance["Recorded At"],
                    errors="coerce"
                ).dt.strftime(
                    "%Y-%m-%d %H:%M"
                )

            st.dataframe(
                attendance,
                hide_index=True,
                use_container_width=True
            )

            # =================================================
            # ATTENDANCE SUMMARY
            # =================================================

            present_count = len(
                attendance[
                    attendance["Status"]
                    .astype(str)
                    .str.lower()
                    == "present"
                ]
            )

            absent_count = len(
                attendance[
                    attendance["Status"]
                    .astype(str)
                    .str.lower()
                    == "absent"
                ]
            )

            attendance_summary_col1, attendance_summary_col2 = (
                st.columns(2)
            )

            attendance_summary_col1.metric(
                "✅ Present",
                present_count
            )

            attendance_summary_col2.metric(
                "❌ Absent",
                absent_count
            )

    # ========================================================
    # TAB 5 — PERFORMANCE
    # ========================================================

    with tab5:

        st.subheader(
            "📈 Student Performance"
        )

        try:

            student_performance_view(
                student_id
            )

        except Exception as e:

            st.error(
                "Unable to load Performance Analytics."
            )

            st.caption(
                f"Details: {e}"
            )
