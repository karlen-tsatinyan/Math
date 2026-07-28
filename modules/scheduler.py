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


def convert_time(time_string):
    """
    Convert:
        4:15 PM
        04:15 PM
    into:
        16:15:00
    """

    if not time_string:
        return "00:00:00"

    time_str = str(time_string).strip()

    try:

        if len(time_str) >= 2 and time_str[1] == ":":
            time_str = "0" + time_str

        return datetime.strptime(
            time_str,
            "%I:%M %p"
        ).strftime("%H:%M:%S")

    except ValueError:

        return time_str


def calculate_end_time(
    date_str,
    time_str,
    duration_minutes
):

    try:

        duration_val = (
            int(duration_minutes)
            if duration_minutes
            else 60
        )

        start_dt = datetime.strptime(
            f"{date_str} {convert_time(time_str)}",
            "%Y-%m-%d %H:%M:%S"
        )

        end_dt = (
            start_dt
            + timedelta(minutes=duration_val)
        )

        return end_dt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    except Exception:

        return f"{date_str}T23:59:59"


# =====================================================
# CACHED DATABASE FETCHERS
# =====================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_scheduler_students():

    return query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        WHERE COALESCE(active, TRUE) = TRUE
        ORDER BY last_name, first_name
        """
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_scheduler_sessions():

    return query_dataframe(
        """
        SELECT
            ss.id,
            ss.student_id,
            ss.session_date::text AS session_date,
            ss.session_time,
            COALESCE(ss.duration, 60) AS duration,
            COALESCE(ss.topic, '') AS topic,
            COALESCE(ss.notes, '') AS notes,
            ss.repeat_type,
            ss.repeat_until,
            ss.recurring_group,
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
# CACHE REFRESH
# =====================================================

def refresh_scheduler_cache():

    get_scheduler_students.clear()
    get_scheduler_sessions.clear()


# =====================================================
# SESSION SCHEDULER
# =====================================================

def scheduler_management():

    # -------------------------------------------------
    # PAGE HEADER
    # -------------------------------------------------

    header_col1, header_col2 = st.columns(
        [5, 1]
    )

    with header_col1:

        st.header(
            "📅 Interactive Session Scheduler"
        )

    with header_col2:

        if st.button(
            "🔄 Refresh Schedule",
            use_container_width=True
        ):

            refresh_scheduler_cache()

            st.session_state.pop(
                "selected_session_id",
                None
            )

            st.session_state.pop(
                "selected_group",
                None
            )

            st.session_state.pop(
                "active_action",
                None
            )

            st.rerun()


    # -------------------------------------------------
    # CALENDAR CSS
    # -------------------------------------------------

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


    student_map = {
        row["name"]: int(row["id"])
        for _, row in students.iterrows()
    }


    # =================================================
    # LOAD SESSIONS
    # =================================================

    sessions = get_scheduler_sessions()


    # =================================================
    # CREATE CALENDAR EVENTS
    # =================================================

    calendar_events = []


    if not sessions.empty:

        for _, row in sessions.iterrows():

            recurring_group = row[
                "recurring_group"
            ]

            is_recurring = (
                pd.notna(recurring_group)
                and str(
                    recurring_group
                ).strip()
                not in [
                    "",
                    "None",
                    "none",
                    "nan"
                ]
            )


            if is_recurring:

                event_color = "#2E7D32"

            else:

                event_color = "#1E88E5"


            session_date = str(
                row["session_date"]
            )

            session_time = str(
                row["session_time"]
            )


            start_iso = (
                f"{session_date}T"
                f"{convert_time(session_time)}"
            )


            end_iso = calculate_end_time(
                session_date,
                session_time,
                row["duration"]
            )


            calendar_events.append(
                {
                    "id": str(row["id"]),

                    "title": (
                        f"{session_time} - "
                        f"{row['student']}"
                    ),

                    "start": start_iso,

                    "end": end_iso,

                    "allDay": False,

                    "backgroundColor": event_color,

                    "borderColor": event_color,

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

                        "group": (
                            str(
                                recurring_group
                            )
                            if is_recurring
                            else ""
                        ),

                    }
                }
            )


    # =================================================
    # TWO COLUMN LAYOUT
    # =================================================

    col_calendar, col_control = st.columns(
        [1.25, 1],
        gap="large"
    )


    # =================================================
    # CALENDAR
    # =================================================

    with col_calendar:

        st.subheader(
            "Monthly Calendar"
        )


        calendar_options = {

            "initialView":
                "dayGridMonth",

            "height":
                480,

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

    if state and "callback" in state:

        callback = state.get(
            "callback"
        )


        # ---------------------------------------------
        # EXISTING SESSION CLICKED
        # ---------------------------------------------

        if callback == "eventClick":

            st.session_state.active_action = (
                "eventClick"
            )


            event_id = (
                state
                .get("eventClick", {})
                .get("event", {})
                .get("id")
            )


            if event_id:

                try:

                    st.session_state.selected_session_id = (
                        int(event_id)
                    )

                except ValueError:

                    st.session_state.selected_session_id = (
                        event_id
                    )


        # ---------------------------------------------
        # EMPTY DATE CLICKED
        # ---------------------------------------------

        elif callback == "dateClick":

            st.session_state.active_action = (
                "dateClick"
            )


            raw_date = (
                state
                .get("dateClick", {})
                .get("dateStr")
                or
                state
                .get("dateClick", {})
                .get("date", "")
            )


            st.session_state.calendar_date = (
                raw_date.split("T")[0]
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
        # EXISTING SESSION
        # =================================================

        if (
            active_action == "eventClick"
            and
            "selected_session_id"
            in st.session_state
        ):

            selected_id = (
                st.session_state
                .selected_session_id
            )


            selected_event = sessions[
                sessions["id"].astype(str)
                ==
                str(selected_id)
            ]


            if not selected_event.empty:

                event = selected_event.iloc[0]


                st.session_state.selected_group = (
                    event["recurring_group"]
                )


                st.subheader(
                    "Manage Session"
                )


                st.warning(
                    f"Selected: {event['student']}"
                )


                st.write(
                    f"📅 **Date:** "
                    f"{event['session_date']}"
                )


                st.write(
                    f"⏰ **Time:** "
                    f"{event['session_time']} "
                    f"({event['duration']} mins)"
                )


                if (
                    pd.notna(event["topic"])
                    and
                    str(event["topic"]).strip()
                ):

                    st.write(
                        f"📖 **Topic:** "
                        f"{event['topic']}"
                    )


                if (
                    pd.notna(event["notes"])
                    and
                    str(event["notes"]).strip()
                ):

                    st.caption(
                        f"📝 Notes: "
                        f"{event['notes']}"
                    )


                # ------------------------------------------------
                # RECURRING INFORMATION
                # ------------------------------------------------

                recurring_group = (
                    event["recurring_group"]
                )


                repeat_type = (
                    event["repeat_type"]
                )


                repeat_until = (
                    event["repeat_until"]
                )


                if (
                    pd.notna(recurring_group)
                    and
                    str(
                        recurring_group
                    ).strip()
                    not in [
                        "",
                        "None",
                        "none",
                        "nan"
                    ]
                ):

                    st.info(
                        "🔄 Part of a recurring "
                        "weekly series."
                    )


                    if (
                        pd.notna(repeat_until)
                        and
                        str(
                            repeat_until
                        ).strip()
                        not in [
                            "",
                            "None",
                            "none",
                            "nan"
                        ]
                    ):

                        st.write(
                            f"📆 **Repeats Until:** "
                            f"{repeat_until}"
                        )


        # =================================================
        # NEW SESSION
        # =================================================

        elif (
            active_action == "dateClick"
            and
            "calendar_date"
            in st.session_state
        ):

            clicked_date = (
                st.session_state
                .calendar_date
            )


            st.subheader(
                "➕ Create New Session"
            )


            st.info(
                f"Selected Date: "
                f"**{clicked_date}**"
            )


            with st.form(
                "new_session_form"
            ):

                selected_student = (
                    st.selectbox(
                        "Student",
                        list(
                            student_map.keys()
                        )
                    )
                )


                selected_time = (
                    st.selectbox(
                        "Start Time",
                        TIME_SLOTS
                    )
                )


                duration = (
                    st.selectbox(
                        "Duration (minutes)",
                        [
                            30,
                            45,
                            60,
                            75,
                            90,
                            120
                        ],
                        index=2
                    )
                )


                topic = st.text_input(
                    "Lesson Topic"
                )


                notes = st.text_area(
                    "Notes"
                )


                recurring = st.checkbox(
                    "Repeat weekly?"
                )


                repeat_until = None


                if recurring:

                    default_until = (
                        datetime.strptime(
                            clicked_date,
                            "%Y-%m-%d"
                        ).date()
                        + timedelta(
                            weeks=4
                        )
                    )


                    repeat_until = st.date_input(
                        "Repeat Until",
                        value=default_until,
                        min_value=datetime.strptime(
                            clicked_date,
                            "%Y-%m-%d"
                        ).date()
                    )


                    st.caption(
                        "The session will be created "
                        "weekly from the selected date "
                        "through the Repeat Until date."
                    )


                save = (
                    st.form_submit_button(
                        "Confirm Reservation",
                        use_container_width=True
                    )
                )


                if save:

                    start_date = datetime.strptime(
                        clicked_date,
                        "%Y-%m-%d"
                    ).date()


                    # ==========================================
                    # SINGLE SESSION
                    # ==========================================

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
                                repeat_until,
                                recurring_group,
                                topic,
                                notes,
                                status
                            )
                            VALUES
                            (
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
                            )
                            """,
                            (
                                student_map[
                                    selected_student
                                ],

                                start_date,

                                selected_time,

                                duration,

                                "None",

                                None,

                                None,

                                topic.strip(),

                                notes.strip(),

                                "Scheduled"
                            )
                        )


                    # ==========================================
                    # RECURRING SESSION
                    # ==========================================

                    else:

                        if repeat_until < start_date:

                            st.error(
                                "Repeat Until date "
                                "cannot be before "
                                "the session date."
                            )

                            st.stop()


                        group_id = str(
                            uuid.uuid4()
                        )


                        current_date = (
                            start_date
                        )


                        while (
                            current_date
                            <= repeat_until
                        ):

                            execute(
                                """
                                INSERT INTO sessions
                                (
                                    student_id,
                                    session_date,
                                    session_time,
                                    duration,
                                    repeat_type,
                                    repeat_until,
                                    recurring_group,
                                    topic,
                                    notes,
                                    status
                                )
                                VALUES
                                (
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
                                )
                                """,
                                (
                                    student_map[
                                        selected_student
                                    ],

                                    current_date,

                                    selected_time,

                                    duration,

                                    "Weekly",

                                    repeat_until,

                                    group_id,

                                    topic.strip(),

                                    notes.strip(),

                                    "Scheduled"
                                )
                            )


                            current_date += (
                                timedelta(
                                    weeks=1
                                )
                            )


                    # ==========================================
                    # REFRESH ONLY SCHEDULER DATA
                    # ==========================================

                    refresh_scheduler_cache()


                    st.session_state.active_action = (
                        None
                    )


                    st.session_state.pop(
                        "calendar_date",
                        None
                    )


                    st.success(
                        "Session(s) created successfully."
                    )


                    st.rerun()


        # =================================================
        # DEFAULT
        # =================================================

        else:

            st.subheader(
                "Interactive Console"
            )


            st.info(
                """
                • Click an empty calendar date
                  to schedule a lesson.

                • Click an existing session
                  to view its details.

                • 🟢 Green sessions are
                  recurring sessions.

                • 🔵 Blue sessions are
                  single sessions.

                • Use **Refresh Schedule**
                  whenever you want to reload
                  the latest database data.
                """
            )


    # =====================================================
    # DELETE SECTION
    # =====================================================

    if (
        active_action == "eventClick"
        and
        "selected_session_id"
        in st.session_state
    ):

        st.divider()


        st.subheader(
            "🗑️ Remove Selected Session"
        )


        selected_id = (
            st.session_state
            .selected_session_id
        )


        group_id = (
            st.session_state.get(
                "selected_group"
            )
        )


        is_recurring = (

            group_id is not None

            and

            str(
                group_id
            ).strip()

            not in [
                "",
                "None",
                "none",
                "nan"
            ]
        )


        if is_recurring:

            delete_option = st.radio(

                "Delete options",

                [
                    "Delete only this session",
                    "Delete entire recurring series"
                ]

            )

        else:

            delete_option = (
                "Delete only this session"
            )


        if st.button(
            "Confirm Delete",
            type="primary"
        ):

            if (
                is_recurring
                and
                delete_option
                ==
                "Delete entire recurring series"
            ):

                execute(
                    """
                    DELETE FROM sessions
                    WHERE recurring_group = %s
                    """,
                    (
                        group_id,
                    )
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


            # ---------------------------------------------
            # Refresh ONLY scheduler cache
            # ---------------------------------------------

            refresh_scheduler_cache()


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
                "Session(s) removed."
            )


            st.rerun()
