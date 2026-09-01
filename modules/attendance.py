import re
from datetime import datetime, date

import pandas as pd
import streamlit as st

from database import query_dataframe, execute
from utils.datetime_utils import today_str

from modules.performance import student_performance_view

# ============================================================

# CACHE SETTINGS

# ============================================================

CACHE_TTL = 300

# ============================================================

# TIME HELPERS

# ============================================================

def parse_session_time(time_value):
"""
Convert a database/Python time value into a datetime.time.

```
Handles examples such as:

    16:15:00
    16:15
    4:15 PM
    04:15 PM
    datetime.time(...)
"""

if time_value is None:
    return None

# --------------------------------------------------------
# Python datetime/time object
# --------------------------------------------------------

if hasattr(time_value, "hour") and hasattr(
    time_value,
    "minute"
):

    try:

        return time_value

    except Exception:

        pass

value = str(
    time_value
).strip()

if not value:

    return None

# --------------------------------------------------------
# Remove possible date portion
# --------------------------------------------------------

if " " in value:

    parts = value.split()

    # Example:
    # 2026-08-31 16:15:00

    if len(parts) >= 2:

        if re.match(
            r"^\d{4}-\d{2}-\d{2}$",
            parts[0]
        ):

            value = " ".join(
                parts[1:]
            )

# --------------------------------------------------------
# Try common formats
# --------------------------------------------------------

formats = [

    "%H:%M:%S",
    "%H:%M",

    "%I:%M %p",
    "%I:%M:%S %p",

    "%I:%M%p",
    "%I:%M:%S%p"
]

for fmt in formats:

    try:

        return datetime.strptime(
            value,
            fmt
        ).time()

    except ValueError:

        continue

return None
```

def parse_session_datetime(
session_date,
session_time
):
"""
Combine session date and time into a Python datetime.
"""

```
# --------------------------------------------------------
# Parse date
# --------------------------------------------------------

if isinstance(
    session_date,
    datetime
):

    date_value = (
        session_date.date()
    )

elif isinstance(
    session_date,
    date
):

    date_value = session_date

else:

    date_text = str(
        session_date
    ).strip()

    date_value = None

    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y"
    ):

        try:

            date_value = datetime.strptime(
                date_text,
                fmt
            ).date()

            break

        except ValueError:

            continue

    if date_value is None:

        return None

# --------------------------------------------------------
# Parse time
# --------------------------------------------------------

time_value = parse_session_time(
    session_time
)

if time_value is None:

    return None

return datetime.combine(
    date_value,
    time_value
)
```

def format_session_time(time_value):
"""
Display database time as a friendly value such as:

```
    4:15 PM
"""

parsed = parse_session_time(
    time_value
)

if parsed is None:

    return str(
        time_value
    )

return parsed.strftime(
    "%I:%M %p"
).lstrip("0")
```

# ============================================================

# STUDENT PROFILE

# ============================================================

def student_profile():

```
st.title(
    "👨‍🎓 Student Profile"
)

# ========================================================
# LOAD STUDENTS
# ========================================================

@st.cache_data(ttl=CACHE_TTL)
def get_students():

    return query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name,
            grade,
            subject,
            email,
            phone,
            zoom_link,
            meeting_id
        FROM students
        ORDER BY
            last_name,
            first_name
        """
    )

students = get_students()

if students.empty:

    st.warning(
        "No students found."
    )

    return

# ========================================================
# STUDENT SELECTOR
# ========================================================

students = students.copy()

# --------------------------------------------------------
# Use ID in the selector so two students with the same
# name cannot be confused.
# --------------------------------------------------------

students["selector_name"] = (
    students["name"].astype(str)
    + " (ID: "
    + students["id"].astype(str)
    + ")"
)

student_selector_map = dict(
    zip(
        students["selector_name"],
        students["id"]
    )
)

selected_label = st.selectbox(
    "Select Student",
    list(
        student_selector_map.keys()
    ),
    key="student_profile_selector"
)

student_id = int(
    student_selector_map[
        selected_label
    ]
)

selected_rows = students[
    students["id"] == student_id
]

if selected_rows.empty:

    st.error(
        "Unable to find the selected student."
    )

    return

student = selected_rows.iloc[0]

# ========================================================
# BASIC INFORMATION
# ========================================================

st.subheader(
    "Student Information"
)

(
    info_col1,
    info_col2,
    info_col3,
    info_col4,
    info_col5
) = st.columns(5)

with info_col1:

    st.caption("Name")

    st.write(
        student["name"]
    )

with info_col2:

    st.caption("Grade")

    st.write(
        student["grade"]
    )

with info_col3:

    st.caption("Subject")

    st.write(
        student["subject"]
    )

with info_col4:

    st.caption("Email")

    st.write(
        student["email"]
        if pd.notna(
            student["email"]
        )
        else "—"
    )

with info_col5:

    st.caption("Phone")

    st.write(
        student["phone"]
        if pd.notna(
            student["phone"]
        )
        else "—"
    )

st.divider()

# ========================================================
# STUDENT OVERVIEW
# ========================================================

@st.cache_data(ttl=120)
def get_student_overview(
    student_id
):

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

overview = get_student_overview(
    student_id
)

if overview.empty:

    payment_total = 0
    session_total = 0
    attendance_total = 0
    homework_total = 0

else:

    row = overview.iloc[0]

    payment_total = float(
        row["payment_total"] or 0
    )

    session_total = int(
        row["session_total"] or 0
    )

    attendance_total = int(
        row["attendance_total"] or 0
    )

    homework_total = int(
        row["homework_total"] or 0
    )

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

@st.cache_data(ttl=120)
def get_next_session(
    student_id,
    current_date
):

    return query_dataframe(
        """
        SELECT
            session_date,
            session_time,
            topic
        FROM sessions
        WHERE student_id = %s
          AND session_date >= %s
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

next_session = get_next_session(
    student_id,
    today_str()
)

if not next_session.empty:

    next_row = next_session.iloc[0]

    next_time = format_session_time(
        next_row["session_time"]
    )

    next_topic = (
        str(
            next_row["topic"]
        ).strip()
        if pd.notna(
            next_row["topic"]
        )
        else ""
    )

    if not next_topic:

        next_topic = (
            "No topic entered"
        )

    st.info(
        f"""
```

**Next Lesson**

📅 {next_row['session_date']}

🕒 {next_time}

📖 {next_topic}
"""
)

```
# ========================================================
# LATEST HOMEWORK GRADE
# ========================================================

@st.cache_data(ttl=120)
def get_latest_grade(
    student_id
):

    return query_dataframe(
        """
        SELECT
            assignment,
            percentage,
            grade_date
        FROM homework_grades
        WHERE student_id = %s
          AND assignment IS NOT NULL
          AND percentage IS NOT NULL
          AND grade_date IS NOT NULL
        ORDER BY
            grade_date DESC,
            id DESC
        LIMIT 1
        """,
        (
            student_id,
        )
    )

latest_grade = get_latest_grade(
    student_id
)

if not latest_grade.empty:

    latest = latest_grade.iloc[0]

    percentage = pd.to_numeric(
        latest["percentage"],
        errors="coerce"
    )

    if pd.notna(
        percentage
    ):

        percentage_display = (
            f"{float(percentage):.1f}%"
        )

    else:

        percentage_display = (
            str(
                latest["percentage"]
            )
        )

    st.success(
        f"""
```

**Latest Homework Grade**

📚 {latest['assignment']}

📊 {percentage_display}

📅 {latest['grade_date']}
"""
)

```
# ========================================================
# TABS
# ========================================================

(
    tab1,
    tab2,
    tab3,
    tab4,
    tab5
) = st.tabs(
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

    @st.cache_data(ttl=120)
    def get_payment_history(
        student_id
    ):

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

    payments = get_payment_history(
        student_id
    )

    if payments.empty:

        st.info(
            "No payments."
        )

    else:

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

    @st.cache_data(ttl=120)
    def get_homework_history(
        student_id
    ):

        return query_dataframe(
            """
            SELECT
                title AS "Homework",
                curriculum_topic AS "Curriculum Topic",
                status AS "Status",
                teacher_feedback AS "Teacher Feedback",
                created_at AS "Assigned"
            FROM homework
            WHERE student_id = %s
            ORDER BY
                created_at DESC
            """,
            (
                student_id,
            )
        )

    homework = get_homework_history(
        student_id
    )

    if homework.empty:

        st.info(
            "No homework."
        )

    else:

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
        "📅 Session History & Attendance"
    )

    # ----------------------------------------------------
    # Load sessions and attendance together.
    #
    # Attendance is matched by:
    #
    # student_id
    # session_date
    # session_time
    #
    # NOT by session ID.
    # ----------------------------------------------------

    @st.cache_data(ttl=60)
    def get_sessions_with_attendance(
        student_id
    ):

        return query_dataframe(
            """
            SELECT

                s.session_date,

                s.session_time,

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
                    THEN 1
                    ELSE 0
                END AS attendance_marked,

                COALESCE(
                    a.status,
                    'Pending'
                ) AS attendance_status

            FROM sessions s

            LEFT JOIN attendance a

                ON a.student_id =
                    s.student_id

                AND a.session_date =
                    s.session_date

                AND a.session_time =
                    s.session_time

            WHERE
                s.student_id = %s

            ORDER BY
                s.session_date DESC,
                s.session_time DESC
            """,
            (
                student_id,
            )
        )

    sessions = get_sessions_with_attendance(
        student_id
    )

    if sessions.empty:

        st.info(
            "No sessions."
        )

    else:

        now = datetime.now()

        # =================================================
        # COMPLETED LESSONS
        # =================================================

        st.markdown(
            "### Completed Lessons"
        )

        completed_count = 0

        for _, row in sessions.iterrows():

            session_datetime = (
                parse_session_datetime(
                    row["session_date"],
                    row["session_time"]
                )
            )

            if session_datetime is None:

                continue

            if session_datetime <= now:

                completed_count += 1

                attendance_marked = (
                    int(
                        row[
                            "attendance_marked"
                        ]
                    )
                    == 1
                )

                topic = str(
                    row["topic"]
                ).strip()

                if not topic:

                    topic = (
                        "No topic entered"
                    )

                formatted_time = (
                    format_session_time(
                        row["session_time"]
                    )
                )

                checkbox_label = (
                    f"📅 {row['session_date']}  |  "
                    f"{formatted_time}  |  "
                    f"📖 {topic}"
                )

                # ------------------------------------------------
                # Attendance checkbox
                #
                # ON  = Present
                # OFF = remove attendance record
                #
                # Uses date/time rather than session ID.
                # ------------------------------------------------

                mark = st.checkbox(
                    checkbox_label,
                    value=attendance_marked,
                    key=(
                        f"attendance_"
                        f"{student_id}_"
                        f"{row['session_date']}_"
                        f"{formatted_time}"
                    )
                )

                # =================================================
                # MARK PRESENT
                # =================================================

                if (
                    mark
                    and not attendance_marked
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
                            status = EXCLUDED.status,
                            marked_at = CURRENT_TIMESTAMP
                        """,
                        (
                            student_id,
                            row["session_date"],
                            row["session_time"],
                            "Present"
                        )
                    )

                    st.cache_data.clear()

                    st.success(
                        "Attendance marked Present."
                    )

                    st.rerun()

                # =================================================
                # REMOVE ATTENDANCE
                # =================================================

                elif (
                    not mark
                    and attendance_marked
                ):

                    execute(
                        """
                        DELETE FROM attendance
                        WHERE student_id = %s
                          AND session_date = %s
                          AND session_time = %s
                        """,
                        (
                            student_id,
                            row["session_date"],
                            row["session_time"]
                        )
                    )

                    st.cache_data.clear()

                    st.warning(
                        "Attendance removed."
                    )

                    st.rerun()

        if completed_count == 0:

            st.info(
                "No completed lessons yet."
            )

        # =================================================
        # UPCOMING LESSONS
        # =================================================

        upcoming_rows = []

        for _, row in sessions.iterrows():

            session_datetime = (
                parse_session_datetime(
                    row["session_date"],
                    row["session_time"]
                )
            )

            if session_datetime is None:

                continue

            if session_datetime > now:

                topic = str(
                    row["topic"]
                ).strip()

                if not topic:

                    topic = (
                        "No topic entered"
                    )

                upcoming_rows.append(
                    {
                        "Date": row[
                            "session_date"
                        ],

                        "Time": (
                            format_session_time(
                                row[
                                    "session_time"
                                ]
                            )
                        ),

                        "Lesson Topic": topic
                    }
                )

        if upcoming_rows:

            st.divider()

            st.markdown(
                "### Upcoming Lessons"
            )

            upcoming_df = pd.DataFrame(
                upcoming_rows
            )

            st.dataframe(
                upcoming_df,
                hide_index=True,
                use_container_width=True
            )

# ========================================================
# TAB 4 — ATTENDANCE
# ========================================================

with tab4:

    st.subheader(
        "✅ Attendance History & Analytics"
    )

    @st.cache_data(ttl=120)
    def get_attendance_history(
        student_id
    ):

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

            WHERE
                a.student_id = %s

            ORDER BY
                a.session_date DESC,
                a.session_time DESC
            """,
            (
                student_id,
            )
        )

    attendance = get_attendance_history(
        student_id
    )

    if attendance.empty:

        st.info(
            "No attendance records."
        )

    else:

        # ------------------------------------------------
        # Format time
        # ------------------------------------------------

        if "Time" in attendance.columns:

            attendance["Time"] = (
                attendance["Time"]
                .apply(
                    format_session_time
                )
            )

        # ------------------------------------------------
        # Format Recorded At
        # ------------------------------------------------

        if "Recorded At" in attendance.columns:

            attendance["Recorded At"] = (
                pd.to_datetime(
                    attendance[
                        "Recorded At"
                    ],
                    errors="coerce"
                )
                .dt.strftime(
                    "%Y-%m-%d %H:%M"
                )
            )

        st.dataframe(
            attendance,
            hide_index=True,
            use_container_width=True
        )

# ========================================================
# TAB 5 — PERFORMANCE
# ========================================================

with tab5:

    student_performance_view(
        student_id
    )
