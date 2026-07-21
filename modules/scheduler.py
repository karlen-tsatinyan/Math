import uuid
from datetime import datetime, timedelta
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
        # Using %I:%M %p ensures 08:00 AM, 01:15 PM, etc. for reliable parsing
        slots.append(current.strftime("%I:%M %p").lstrip("0"))
        current += timedelta(minutes=15)

    return slots

TIME_SLOTS = generate_time_slots()

def convert_time(time_string):
    """
    Convert '4:15 PM' or '04:15 PM' into '16:15:00'
    """
    # Stripping space and unifying format
    time_str = time_string.strip()
    if len(time_str.split(":")[0]) == 1:
        time_str = "0" + time_str
    return datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M:%S")

def calculate_end_time(date_str, time_str, duration_minutes):
    """
    Returns ISO datetime string for FullCalendar end time
    """
    start_dt = datetime.strptime(f"{date_str} {convert_time(time_str)}", "%Y-%m-%d %H:%M:%S")
    end_dt = start_dt + timedelta(minutes=int(duration_minutes))
    return end_dt.strftime("%Y-%m-%dT%H:%M:%S")


# =====================================================
# SESSION SCHEDULER MATRIX
# =====================================================

def scheduler_management():
    st.header("📅 Interactive Session Scheduler Matrix")

    # Compact calendar size styling
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
    # STUDENT LIST
    # =================================================
    students = query_dataframe(
        """
        SELECT 
            id, 
            first_name || ' ' || last_name AS name 
        FROM students 
        ORDER BY last_name
        """
    )

    if students.empty:
        st.info("Enroll students first.")
        return

    student_map = {row["name"]: row["id"] for _, row in students.iterrows()}

    # =================================================
    # LOAD SESSIONS
    # =================================================
    sessions = query_dataframe(
        """
        SELECT 
            sessions.id,
            sessions.student_id,
            sessions.session_date,
            sessions.session_time,
            sessions.duration,
            sessions.topic,
            sessions.notes,
            sessions.recurring_group,
            sessions.status,
            students.first_name || ' ' || students.last_name AS student
        FROM sessions
        JOIN students ON sessions.student_id = students.id
        ORDER BY session_date, session_time
        """
    )

    # =================================================
    # CREATE CALENDAR EVENTS
    # =================================================
    calendar_events = []

    for _, row in sessions.iterrows():
        # Determine color based on recurrence
        is_recurring = (
            row["recurring_group"] is not None 
            and str(row["recurring_group"]).strip() not in ["nan", "", "None"]
        )
        color = "#2E7D32" if is_recurring else "#1E88E5"
        
        start_iso = f"{row['session_date']}T{convert_time(row['session_time'])}"
        end_iso = calculate_end_time(row["session_date"], row["session_time"], row.get("duration", 60))

        calendar_events.append({
            "id": str(row["id"]),
            "title": f"{row['session_time']} - {row['student']}",
            "start": start_iso,
            "end": end_iso,
            "allDay": False,
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "student": str(row["student"]),
                "topic": str(row["topic"]) if row["topic"] else "",
                "notes": str(row["notes"]) if row["notes"] else "",
                "group": str(row["recurring_group"]) if is_recurring else ""
            }
        })

    # =================================================
    # TWO COLUMN LAYOUT
    # =================================================
    col_calendar, col_control = st.columns([1.25, 1], gap="large")

    with col_calendar:
        st.subheader("Monthly Calendar")
        
        calendar_options = {
            "initialView": "dayGridMonth",
            "height": 480,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth"
            },
            "eventOrder": "start",
            "displayEventTime": False,
            "selectable": True,
            "editable": False
        }

        state = calendar(
            events=calendar_events,
            options=calendar_options,
            key="scheduler_matrix"
        )

    # State update handling from Calendar
    if state and "callback" in state:
        cb = state.get("callback")
        if cb == "eventClick":
            st.session_state.active_action = "eventClick"
            event_id = state.get("eventClick", {}).get("event", {}).get("id")
            if event_id:
                st.session_state.selected_session_id = int(event_id)
        elif cb == "dateClick":
            st.session_state.active_action = "dateClick"
            raw_date = state.get("dateClick", {}).get("dateStr") or state.get("dateClick", {}).get("date", "")
            st.session_state.calendar_date = raw_date.split("T")[0]
            # Clear selection when clicking a new date
            st.session_state.pop("selected_session_id", None)
            st.session_state.pop("selected_group", None)

    active_action = st.session_state.get("active_action")

    # =================================================
    # RIGHT CONTROL PANEL
    # =================================================
    with col_control:

        # ---------------------------------------------
        # EXISTING SESSION CLICKED
        # ---------------------------------------------
        if active_action == "eventClick" and "selected_session_id" in st.session_state:
            selected_id = st.session_state.selected_session_id
            selected_event = sessions[sessions["id"] == selected_id]

            if not selected_event.empty:
                event = selected_event.iloc[0]
                st.session_state.selected_group = event["recurring_group"]

                st.subheader("Manage Session")
                st.warning(f"Selected: {event['student']}")
                st.write(f"📅 **Date:** {event['session_date']}")
                st.write(f"⏰ **Time:** {event['session_time']} ({event['duration']} mins)")
                
                if event["topic"]:
                    st.write(f"📖 **Topic:** {event['topic']}")
                if event["notes"]:
                    st.caption(f"📝 Notes: {event['notes']}")
                if event["recurring_group"]:
                    st.info("🔄 Part of a recurring series.")

        # ---------------------------------------------
        # EMPTY DATE CLICKED
        # ---------------------------------------------
        elif active_action == "dateClick" and "calendar_date" in st.session_state:
            clicked_date = st.session_state.calendar_date

            st.subheader("➕ Create New Session")
            st.info(f"Selected Date: **{clicked_date}**")

            with st.form("new_session_form"):
                selected_student = st.selectbox("Student", list(student_map.keys()))
                selected_time = st.selectbox("Start Time", TIME_SLOTS)
                duration = st.selectbox("Duration (minutes)", [30, 45, 60, 75, 90, 120], index=2)
                topic = st.text_input("Lesson Topic")
                notes = st.text_area("Notes")
                recurring = st.checkbox("Repeat weekly?")
                
                weeks = 1
                if recurring:
                    weeks = st.number_input("Number of weeks", min_value=2, max_value=52, value=4)

                save = st.form_submit_button("Confirm Reservation", use_container_width=True)

                if save:
                    group_id = str(uuid.uuid4()) if recurring else None
                    start_date = datetime.strptime(clicked_date, "%Y-%m-%d").date()

                    for i in range(int(weeks)):
                        session_day = start_date + timedelta(weeks=i)
                        execute(
                            """
                            INSERT INTO sessions (
                                student_id, session_date, session_time, duration,
                                repeat_type, recurring_group, topic, notes, status
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                student_map[selected_student],
                                str(session_day),
                                selected_time,
                                duration,
                                "Weekly" if recurring else "None",
                                group_id,
                                topic,
                                notes,
                                "Scheduled"
                            )
                        )

                    st.success("Session(s) created successfully.")
                    st.session_state.active_action = None
                    st.rerun()

        # ---------------------------------------------
        # DEFAULT / NO SELECTION
        # ---------------------------------------------
        else:
            st.subheader("Interactive Console")
            st.info(
                """
                • Click an empty calendar date to schedule a lesson.
                
                • Click an existing colored session to view or manage it.
                
                • **Green** sessions belong to recurring series.
                
                • **Blue** sessions are single events.
                """
            )

    # =================================================
    # DELETE SECTION
    # =================================================
    if active_action == "eventClick" and "selected_session_id" in st.session_state:
        st.divider()
        st.subheader("🗑️ Remove Selected Session")

        selected_id = st.session_state.selected_session_id
        group_id = st.session_state.get("selected_group")

        is_recurring = group_id is not None and str(group_id).strip() not in ["nan", "", "None"]

        if is_recurring:
            delete_option = st.radio(
                "Delete options",
                ["Delete only this session", "Delete entire recurring series"]
            )
        else:
            delete_option = "Delete only this session"

        if st.button("Confirm Delete", type="primary"):
            if is_recurring and delete_option == "Delete entire recurring series":
                execute("DELETE FROM sessions WHERE recurring_group=?", (group_id,))
            else:
                execute("DELETE FROM sessions WHERE id=?", (selected_id,))

            st.success("Session(s) removed.")
            
            # Clean up session state
            st.session_state.pop("selected_session_id", None)
            st.session_state.pop("selected_group", None)
            st.session_state.active_action = None
            st.rerun()
