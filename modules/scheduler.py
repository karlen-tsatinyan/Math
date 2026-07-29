import uuid
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

from database import execute, query_dataframe


# =====================================================
# TIME SLOT HELPERS
# =====================================================

def generate_time_slots():
    """
    Generate 15-minute time slots from 8:00 AM through 8:00 PM.
    """
    slots = []

    start = datetime.strptime("08:00 AM", "%I:%M %p")
    end = datetime.strptime("08:00 PM", "%I:%M %p")

    current = start

    while current <= end:
        slots.append(
            current.strftime("%I:%M %p").lstrip("0")
        )

        current += timedelta(minutes=15)

    return slots


TIME_SLOTS = generate_time_slots()


# =====================================================
# TIME CONVERSION
# =====================================================

def convert_time(time_value):
    """
    Convert common PostgreSQL/Python time values into HH:MM:SS.

    Handles examples such as:
        4:15 PM
        04:15 PM
        16:15:00
        16:15
        datetime.time(...)
    """

    if time_value is None:
        return "00:00:00"

    # PostgreSQL time / Python datetime.time
    if hasattr(time_value, "strftime"):
        try:
            return time_value.strftime("%H:%M:%S")
        except Exception:
            pass

    time_str = str(time_value).strip()

    if not time_str:
        return "00:00:00"

    # Already 24-hour time
    for fmt in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M %p",
        "%I:%M:%S %p",
    ):
        try:
            return datetime.strptime(
                time_str,
                fmt
            ).strftime("%H:%M:%S")

        except ValueError:
            continue

    return time_str


# =====================================================
# DISPLAY TIME
# =====================================================

def display_time(time_value):
    """
    Convert database time into a friendly format such as:
    4:15 PM
    """

    converted = convert_time(time_value)

    try:
        return datetime.strptime(
            converted,
            "%H:%M:%S"
        ).strftime("%-I:%M %p")

    except Exception:

        try:
            return datetime.strptime(
                converted,
                "%H:%M:%S"
            ).strftime("%I:%M %p").lstrip("0")

        except Exception:
            return str(time_value)


# =====================================================
# END TIME
# =====================================================

def calculate_end_time(
    date_str,
    time_value,
    duration_minutes
):
    """
    Calculate FullCalendar end datetime.
    """

    try:

        duration = int(
            duration_minutes
            if duration_minutes
            else 60
        )

        start_dt = datetime.strptime(
            f"{date_str} {convert_time(time_value)}",
            "%Y-%m-%d %H:%M:%S"
        )

        end_dt = (
            start_dt
            + timedelta(minutes=duration)
        )

        return end_dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    except Exception:

        return f"{date_str}T23:59:59"


# =====================================================
# CACHED STUDENT LIST
# =====================================================

@st.cache_data(ttl=600)
def get_scheduler_students():

    return query_dataframe(
        """
        SELECT
            id,
            first_name,
            last_name
        FROM students
        ORDER BY last_name, first_name
        """
    )


# =====================================================
# CACHED SESSION LIST
# =====================================================

@st.cache_data(ttl=600)
def get_scheduler_sessions():

    return query_dataframe(
        """
        SELECT
            ss.id,
            ss.student_id,

            ss.session_date::text AS session_date,

            ss.session_time,

            COALESCE(
                ss.duration,
                60
            ) AS duration,

            COALESCE(
                ss.repeat_type,
                'None'
            ) AS repeat_type,

            ss.recurring_group,

            ss.not_after::text AS not_after,

            COALESCE(
                ss.topic,
                ''
            ) AS topic,

            COALESCE(
                ss.notes,
                ''
            ) AS notes,

            COALESCE(
                ss.status,
                'Scheduled'
            ) AS status,

            s.first_name || ' ' || s.last_name
                AS student

        FROM sessions ss

        JOIN students s
            ON ss.student_id = s.id

        ORDER BY
            ss.session_date,
            ss.session_time
        """
    )


# =====================================================
# CLEAR ONLY SCHEDULER CACHE
# =====================================================

def refresh_scheduler_data():

    get_scheduler_students.clear()
    get_scheduler_sessions.clear()


# =====================================================
# CREATE CALENDAR EVENTS
# =====================================================

def build_calendar_events(sessions):

    events = []

    if sessions.empty:
        return events

    for _, row in sessions.iterrows():

        recurring_group = row.get(
            "recurring_group"
        )

        is_recurring = (
            recurring_group is not None
            and str(
                recurring_group
            ).strip()
            not in [
                "",
                "nan",
                "None",
                "none"
            ]
        )

        if is_recurring:
            color = "#2E7D32"
        else:
            color = "#1E88E5"

        session_date = str(
            row["session_date"]
        )

        session_time = row[
            "session_time"
        ]

        start_time = convert_time(
            session_time
        )

        end_time = calculate_end_time(
            session_date,
            session_time,
            row.get("duration", 60)
        )

        events.append(
            {
                "id": str(row["id"]),

                "title": (
                    f"{display_time(session_time)} "
                    f"- {row['student']}"
                ),

                "start": (
                    f"{session_date}T"
                    f"{start_time}"
                ),

                "end": end_time,

                "allDay": False,

                "backgroundColor": color,

                "borderColor": color,

                "extendedProps": {
                    "student": str(
                        row["student"]
                    ),

                    "topic": str(
                        row["topic"]
                    ),

                    "notes": str(
                        row["notes"]
                    ),

                    "status": str(
                        row["status"]
                    ),

                    "group": (
                        str(recurring_group)
                        if is_recurring
                        else ""
                    )
                }
            }
        )

    return events


# =====================================================
# SESSION SCHEDULER
# =====================================================

def scheduler_management():

    st.header(
        "📅 Interactive Session Scheduler"
    )

    # =================================================
    # REFRESH BUTTON
    # =================================================

    refresh_col, info_col = st.columns(
        [1, 4]
    )

    with refresh_col:

        if st.button(
            "🔄 Refresh Schedule",
            use_container_width=True
        ):

            refresh_scheduler_data()

            st.session_state.pop(
                "selected_session_id",
                None
            )

            st.session_state.pop(
                "selected_group",
                None
            )

            st.session_state.active_action = None

            st.rerun()

    with info_col:

        st.caption(
            "Schedule data is cached for faster loading. "
            "Use Refresh Schedule after changes made elsewhere."
        )

    # =================================================
    # COMPACT CALENDAR CSS
    # =================================================

    st.markdown(
        """
        <style>

        .fc {
            max-height: 520px !important;
            font-size: 0.85em !important;
        }

        .fc .fc-scroller-harness {
            max-height: 430px !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # =================================================
    # LOAD STUDENTS
    # =================================================

    students = get_scheduler_students()

    if students.empty:

        st.info(
            "Enroll students first."
        )

        return

    students = students.copy()

    students["name"] = (
        students["first_name"].astype(str)
        + " "
        + students["last_name"].astype(str)
    )

    student_map = dict(
        zip(
            students["name"],
            students["id"]
        )
    )

    # =================================================
    # LOAD SESSIONS
    # =================================================

    sessions = get_scheduler_sessions()

    # =================================================
    # BUILD CALENDAR EVENTS
    # =================================================

    calendar_events = build_calendar_events(
        sessions
    )

    # =================================================
    # TWO COLUMN LAYOUT
    # =================================================

    col_calendar, col_control = st.columns(
        [1.35, 1],
        gap="large"
    )

    # =================================================
    # CALENDAR
    # =================================================

    with col_calendar:

        st.subheader(
            "📅 Monthly Calendar"
        )

        calendar_options = {

            "initialView":
                "dayGridMonth",

            "height":
                500,

            "headerToolbar": {

                "left":
                    "prev,next today",

                "center":
                    "title",

                "right":
                    "dayGridMonth"
            },

            "eventOrder":
                "start",

            "displayEventTime":
                False,

            "selectable":
                True,

            "editable":
                False
        }

        state = calendar(
            events=calendar_events,
            options=calendar_options,
            key="scheduler_matrix"
        )

    # =================================================
    # HANDLE CALENDAR CALLBACK
    # =================================================

    if state and state.get("callback"):

        callback = state.get(
            "callback"
        )

        # ---------------------------------------------
        # EXISTING SESSION CLICKED
        # ---------------------------------------------

        if callback == "eventClick":

            event_data = state.get(
                "eventClick",
                {}
            )

            event = event_data.get(
                "event",
                {}
            )

            event_id = event.get(
                "id"
            )

            if event_id:

                try:

                    st.session_state.selected_session_id = int(
                        event_id
                    )

                except Exception:

                    st.session_state.selected_session_id = (
                        event_id
                    )

                st.session_state.active_action = (
                    "eventClick"
                )

        # ---------------------------------------------
        # EMPTY DATE CLICKED
        # ---------------------------------------------

        elif callback == "dateClick":

            date_data = state.get(
                "dateClick",
                {}
            )

            raw_date = (
                date_data.get("dateStr")
                or date_data.get("date")
                or ""
            )

            clicked_date = str(
                raw_date
            ).split("T")[0]

            st.session_state.calendar_date = (
                clicked_date
            )

            st.session_state.active_action = (
                "dateClick"
            )

            st.session_state.pop(
                "selected_session_id",
                None
            )

            st.session_state.pop(
                "selected_group",
                None
            )

    active_action = st.session_state.get(
        "active_action"
    )

    # =================================================
    # RIGHT CONTROL PANEL
    # =================================================

    with col_control:

        # =================================================
        # EDIT EXISTING SESSION
        # =================================================

        if (
            active_action == "eventClick"
            and "selected_session_id"
            in st.session_state
        ):

            selected_id = (
                st.session_state
                .selected_session_id
            )

            selected_rows = sessions[
                sessions["id"].astype(str)
                == str(selected_id)
            ]

            if selected_rows.empty:

                st.warning(
                    "The selected session could not be found."
                )

                return

            event = selected_rows.iloc[0]

            recurring_group = (
                event["recurring_group"]
            )

            st.session_state.selected_group = (
                recurring_group
            )

            is_recurring = (
                recurring_group is not None
                and str(
                    recurring_group
                ).strip()
                not in [
                    "",
                    "nan",
                    "None",
                    "none"
                ]
            )

            st.subheader(
                "✏️ Edit Session"
            )

            st.info(
                f"Student: **{event['student']}**"
            )

            # ---------------------------------------------
            # CURRENT INFORMATION
            # ---------------------------------------------

            try:

                current_date = datetime.strptime(
                    str(event["session_date"]),
                    "%Y-%m-%d"
                ).date()

            except Exception:

                current_date = datetime.today().date()

            current_time = display_time(
                event["session_time"]
            )

            try:

                current_time_index = (
                    TIME_SLOTS.index(
                        current_time
                    )
                )

            except ValueError:

                current_time_index = 0

            try:

                current_duration = int(
                    event["duration"]
                )

            except Exception:

                current_duration = 60

            duration_options = [
                30,
                45,
                60,
                75,
                90,
                120
            ]

            if current_duration not in duration_options:

                duration_options.append(
                    current_duration
                )

                duration_options.sort()

            # ---------------------------------------------
            # EDIT FORM
            # ---------------------------------------------

            with st.form(
                f"edit_session_form_{selected_id}"
            ):

                edit_student = st.selectbox(
                    "Student",
                    list(
                        student_map.keys()
                    ),
                    index=(
                        list(
                            student_map.values()
                        ).index(
                            event["student_id"]
                        )
                    )
                )

                edit_date = st.date_input(
                    "Session Date",
                    value=current_date
                )

                edit_time = st.selectbox(
                    "Start Time",
                    TIME_SLOTS,
                    index=current_time_index
                )

                edit_duration = st.selectbox(
                    "Duration (minutes)",
                    duration_options,
                    index=duration_options.index(
                        current_duration
                    )
                )

                edit_topic = st.text_input(
                    "Lesson Topic",
                    value=str(
                        event["topic"]
                    )
                    if pd.notna(
                        event["topic"]
                    )
                    else ""
                )

                edit_notes = st.text_area(
                    "Notes",
                    value=str(
                        event["notes"]
                    )
                    if pd.notna(
                        event["notes"]
                    )
                    else ""
                )

                status_options = [
                    "Scheduled",
                    "Completed",
                    "Cancelled",
                    "No Show"
                ]

                current_status = str(
                    event["status"]
                )

                if current_status not in status_options:

                    status_options.append(
                        current_status
                    )

                edit_status = st.selectbox(
                    "Status",
                    status_options,
                    index=status_options.index(
                        current_status
                    )
                )

                # -----------------------------------------
                # RECURRING SESSION
                # -----------------------------------------

                if is_recurring:

                    st.markdown(
                        "### 🔄 Recurring Series"
                    )

                    st.caption(
                        "This session belongs to a weekly recurring series."
                    )

                    existing_not_after = (
                        event["not_after"]
                    )

                    if (
                        existing_not_after
                        and str(
                            existing_not_after
                        ).strip()
                        not in [
                            "",
                            "None",
                            "nan"
                        ]
                    ):

                        try:

                            current_not_after = (
                                datetime.strptime(
                                    str(
                                        existing_not_after
                                    ),
                                    "%Y-%m-%d"
                                ).date()
                            )

                        except Exception:

                            current_not_after = (
                                edit_date
                            )

                    else:

                        current_not_after = (
                            edit_date
                        )

                    edit_not_after = st.date_input(
                        "Repeat Until",
                        value=current_not_after
                    )

                    edit_scope = st.radio(
                        "Apply changes to",
                        [
                            "This session only",
                            "Entire recurring series"
                        ]
                    )

                else:

                    edit_not_after = None

                    edit_scope = (
                        "This session only"
                    )

                save_edit = st.form_submit_button(
                    "💾 Save Changes",
                    use_container_width=True,
                    type="primary"
                )

            # ---------------------------------------------
            # SAVE EDIT
            # ---------------------------------------------

            if save_edit:

                if (
                    is_recurring
                    and edit_not_after
                    and edit_not_after < edit_date
                ):

                    st.error(
                        "Repeat Until cannot be earlier than the session date."
                    )

                else:

                    try:

                        if (
                            is_recurring
                            and edit_scope
                            == "Entire recurring series"
                        ):

                            # ---------------------------------
                            # Update the entire recurring series
                            # ---------------------------------

                            execute(
                                """
                                UPDATE sessions
                                SET
                                    student_id = %s,
                                    session_time = %s,
                                    duration = %s,
                                    topic = %s,
                                    notes = %s,
                                    status = %s,
                                    not_after = %s
                                WHERE recurring_group = %s
                                """,
                                (
                                    student_map[
                                        edit_student
                                    ],

                                    edit_time,

                                    edit_duration,

                                    edit_topic.strip(),

                                    edit_notes.strip(),

                                    edit_status,

                                    edit_not_after,

                                    recurring_group
                                )
                            )

                        else:

                            # ---------------------------------
                            # Update only selected session
                            # ---------------------------------

                            execute(
                                """
                                UPDATE sessions
                                SET
                                    student_id = %s,
                                    session_date = %s,
                                    session_time = %s,
                                    duration = %s,
                                    topic = %s,
                                    notes = %s,
                                    status = %s,
                                    not_after = %s
                                WHERE id = %s
                                """,
                                (
                                    student_map[
                                        edit_student
                                    ],

                                    edit_date,

                                    edit_time,

                                    edit_duration,

                                    edit_topic.strip(),

                                    edit_notes.strip(),

                                    edit_status,

                                    edit_not_after,

                                    selected_id
                                )
                            )

                        # -----------------------------------------
                        # Refresh ONLY scheduler cache
                        # -----------------------------------------

                        refresh_scheduler_data()

                        st.session_state.pop(
                            "selected_session_id",
                            None
                        )

                        st.session_state.pop(
                            "selected_group",
                            None
                        )

                        st.session_state.active_action = (
                            None
                        )

                        st.success(
                            "Session updated successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to update session: {e}"
                        )

            # ---------------------------------------------
            # SERIES INFORMATION
            # ---------------------------------------------

            if is_recurring:

                st.info(
                    "🔄 This is part of a recurring weekly series."
                )

        # =================================================
        # CREATE NEW SESSION
        # =================================================

        elif (
            active_action == "dateClick"
            and "calendar_date" in st.session_state
        ):

            clicked_date = st.session_state.calendar_date

            try:
                selected_date = datetime.strptime(
                    clicked_date,
                    "%Y-%m-%d"
                ).date()

            except Exception:
                selected_date = datetime.today().date()

            st.subheader("➕ Create New Session")

            st.info(
                f"Selected Date: **{selected_date.strftime('%B %d, %Y')}**"
            )

            # -------------------------------------------------
            # ONE SINGLE FORM
            # -------------------------------------------------

            with st.form("new_session_form", clear_on_submit=False):

                selected_student = st.selectbox(
                    "Student",
                    list(student_map.keys()),
                    key="new_session_student"
                )

                selected_time = st.selectbox(
                    "Start Time",
                    TIME_SLOTS,
                    key="new_session_time"
                )

                duration = st.selectbox(
                    "Duration (minutes)",
                    [30, 45, 60, 75, 90, 120],
                    index=2,
                    key="new_session_duration"
                )

                topic = st.text_input(
                    "Lesson Topic",
                    key="new_session_topic"
                )

                notes = st.text_area(
                    "Notes",
                    key="new_session_notes"
                )

                st.markdown("### 🔄 Recurring Session")

                recurring = st.checkbox(
                    "Repeat this session weekly",
                    value=False,
                    key="new_session_recurring"
                )

                # -------------------------------------------------
                # ONLY SHOW REPEAT UNTIL WHEN RECURRING IS CHECKED
                # -------------------------------------------------

                if recurring:

                    default_repeat_until = (
                        selected_date + timedelta(weeks=4)
                    )

                    repeat_until = st.date_input(
                        "Repeat Until",
                        value=default_repeat_until,
                        min_value=selected_date,
                        key="new_session_repeat_until"
                    )

                    st.caption(
                        f"Weekly sessions will be created from "
                        f"{selected_date.strftime('%b %d, %Y')} "
                        f"through "
                        f"{repeat_until.strftime('%b %d, %Y')}."
                    )

                else:

                    repeat_until = None

                st.divider()

                save = st.form_submit_button(
                    "💾 Confirm Reservation",
                    use_container_width=True,
                    type="primary"
                )

            # =================================================
            # PROCESS SUBMISSION
            # =================================================

            if save:

                # -------------------------------------------------
                # VALIDATE
                # -------------------------------------------------

                if recurring and repeat_until is None:

                    st.error(
                        "Please select a Repeat Until date."
                    )

                elif (
                    recurring
                    and repeat_until < selected_date
                ):

                    st.error(
                        "Repeat Until must be on or after "
                        "the first session date."
                    )

                else:

                    try:

                        student_id = int(
                            student_map[selected_student]
                        )

                        # =================================================
                        # SINGLE SESSION
                        # =================================================

                        if not recurring:

                            execute(
                                """
                                INSERT INTO sessions
                                (
                                    student_id,
                                    session_date,
                                    session_time,
                                    duration,
                                    repeat_type,
                                    recurring_group,
                                    not_after,
                                    topic,
                                    notes,
                                    status
                                )
                                SELECT
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    NULL,
                                    NULL,
                                    %s,
                                    %s,
                                    %s
                                WHERE NOT EXISTS (
                                    SELECT 1
                                    FROM sessions
                                    WHERE
                                        student_id = %s
                                        AND session_date = %s
                                        AND session_time = %s
                                )
                                """,
                                (
                                    student_id,
                                    selected_date,
                                    selected_time,
                                    int(duration),
                                    "None",
                                    topic.strip(),
                                    notes.strip(),
                                    "Scheduled",

                                    # duplicate check
                                    student_id,
                                    selected_date,
                                    selected_time
                                )
                            )

                            message = (
                                "Session created successfully."
                            )

                        # =================================================
                        # RECURRING WEEKLY SERIES
                        # =================================================

                        else:

                            group_id = str(uuid.uuid4())

                            current_date = selected_date
                            session_count = 0

                            while current_date <= repeat_until:

                                execute(
                                    """
                                    INSERT INTO sessions
                                    (
                                        student_id,
                                        session_date,
                                        session_time,
                                        duration,
                                        repeat_type,
                                        recurring_group,
                                        not_after,
                                        topic,
                                        notes,
                                        status
                                    )
                                    SELECT
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s,
                                        %s
                                    WHERE NOT EXISTS (
                                        SELECT 1
                                        FROM sessions
                                        WHERE
                                            student_id = %s
                                            AND session_date = %s
                                            AND session_time = %s
                                    )
                                    """,
                                    (
                                        student_id,
                                        current_date,
                                        selected_time,
                                        int(duration),
                                        "Weekly",
                                        group_id,
                                        repeat_until,
                                        topic.strip(),
                                        notes.strip(),
                                        "Scheduled",

                                        # duplicate protection
                                        student_id,
                                        current_date,
                                        selected_time
                                    )
                                )

                                session_count += 1

                                current_date += timedelta(
                                    weeks=1
                                )

                            message = (
                                f"{session_count} weekly sessions "
                                f"created successfully."
                            )

                        # =================================================
                        # CLEAR SCHEDULER STATE BEFORE RERUN
                        # =================================================

                        refresh_scheduler_data()

                        st.session_state.pop(
                            "calendar_date",
                            None
                        )

                        st.session_state.pop(
                            "selected_session_id",
                            None
                        )

                        st.session_state.pop(
                            "selected_group",
                            None
                        )

                        st.session_state.active_action = None

                        st.success(message)

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to create session: {e}"
                        )

        # =================================================
        # DEFAULT
        # =================================================

        else:

            st.subheader(
                "Interactive Console"
            )

            st.info(
                """
                **➕ Create:** Click an empty calendar date.

                **✏️ Edit:** Click an existing session.

                **🔄 Recurring:** Green sessions belong to a weekly series.

                **🔵 Single:** Blue sessions are individual sessions.

                **🗑️ Delete:** Select an existing session to access deletion controls.
                """
            )

    # =====================================================
    # DELETE SECTION
    # =====================================================

    if (
        active_action == "eventClick"
        and "selected_session_id"
        in st.session_state
    ):

        selected_id = (
            st.session_state.selected_session_id
        )

        selected_rows = sessions[
            sessions["id"].astype(str)
            == str(selected_id)
        ]

        if not selected_rows.empty:

            event = selected_rows.iloc[0]

            recurring_group = (
                event["recurring_group"]
            )

            is_recurring = (
                recurring_group is not None
                and str(
                    recurring_group
                ).strip()
                not in [
                    "",
                    "nan",
                    "None",
                    "none"
                ]
            )

            st.divider()

            st.subheader(
                "🗑️ Remove Selected Session"
            )

            if is_recurring:

                delete_option = st.radio(
                    "Delete options",
                    [
                        "Delete only this session",
                        "Delete entire recurring series"
                    ],
                    key=f"delete_option_{selected_id}"
                )

            else:

                delete_option = (
                    "Delete only this session"
                )

            if st.button(
                "🗑️ Confirm Delete",
                type="primary",
                key=f"delete_session_{selected_id}"
            ):

                try:

                    if (
                        is_recurring
                        and delete_option
                        == "Delete entire recurring series"
                    ):

                        execute(
                            """
                            DELETE FROM sessions
                            WHERE recurring_group = %s
                            """,
                            (
                                recurring_group,
                            )
                        )

                        delete_message = (
                            "Entire recurring series deleted."
                        )

                    else:

                        execute(
                            """
                            DELETE FROM sessions
                            WHERE id = %s
                            """,
                            (
                                selected_id,
                            )
                        )

                        delete_message = (
                            "Selected session deleted."
                        )

                    # -----------------------------------------
                    # Refresh ONLY scheduler cache
                    # -----------------------------------------

                    refresh_scheduler_data()

                    st.session_state.pop(
                        "selected_session_id",
                        None
                    )

                    st.session_state.pop(
                        "selected_group",
                        None
                    )

                    st.session_state.active_action = (
                        None
                    )

                    st.success(
                        delete_message
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Unable to delete session: {e}"
                    )
