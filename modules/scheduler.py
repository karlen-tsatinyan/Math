import streamlit as st
from datetime import date, datetime, timedelta
import uuid

from streamlit_calendar import calendar

from database import execute, query_dataframe


# =====================================================
# 15 MINUTE TIME SLOT GENERATOR
# =====================================================

def generate_time_slots():

    slots = []

    start = datetime.strptime(
        "8:00 AM",
        "%I:%M %p"
    )

    end = datetime.strptime(
        "8:00 PM",
        "%I:%M %p"
    )

    current = start

    while current <= end:

        slots.append(
            current.strftime("%-I:%M %p")
        )

        current += timedelta(
            minutes=15
        )

    return slots


TIME_SLOTS = generate_time_slots()

def convert_time(time_string):

    """
    Convert:
    4:15 PM

    into:
    16:15:00
    """

    return datetime.strptime(
        time_string,
        "%I:%M %p"
    ).strftime(
        "%H:%M:%S"
    )

# =====================================================
# SESSION SCHEDULER MATRIX
# =====================================================

def scheduler_management():


    st.header(
        "📅 Interactive Session Scheduler Matrix"
    )


    # Compact calendar size
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

        st.info(
            "Enroll students first."
        )

        return



    student_map = {
        row["name"]: row["id"]
        for _, row in students.iterrows()
    }



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

            sessions.topic,

            sessions.notes,

            sessions.recurring_group,

            sessions.status,

            students.first_name ||
            ' ' ||
            students.last_name AS student


        FROM sessions


        JOIN students

        ON sessions.student_id = students.id


        ORDER BY

            session_date,

            session_time

        """
    )



    # =================================================
    # CREATE CALENDAR EVENTS
    # =================================================

    calendar_events = []


    for _, row in sessions.iterrows():

        # Determine color safely
        if (
            row["recurring_group"] is not None
            and str(row["recurring_group"]) != "nan"
            and str(row["recurring_group"]) != ""
        ):
            color = "#2E7D32"
        else:
            color = "#1E88E5"


        calendar_events.append(

            {
                "id":
                    str(row["id"]),


                # IMPORTANT:
                # Keep time in title because we disable FullCalendar time display
                "title":
                    f"{row['session_time']} - {row['student']}",


                # IMPORTANT:
                # Full datetime for chronological sorting
                "start":
                    f"{row['session_date']}T{convert_time(row['session_time'])}",


                "allDay":
                    False,


                "backgroundColor":
                    color,


                "borderColor":
                    color,


                "extendedProps":
                    {

                        "student":
                            str(row["student"]),


                        "topic":
                            str(row["topic"])
                            if row["topic"] is not None
                            else "",


                        "notes":
                            str(row["notes"])
                            if row["notes"] is not None
                            else "",


                        "group":
                            str(row["recurring_group"])
                            if row["recurring_group"] is not None
                            else ""

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
    # CALENDAR GRID
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


            "headerToolbar":
                {

                    "left":
                        "prev,next today",

                    "center":
                        "title",

                    "right":
                        "dayGridMonth"

                },


            # Sort by real start datetime
            "eventOrder":
                "start",


            # IMPORTANT:
            # Prevent duplicate time display
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
    # RIGHT CONTROL PANEL
    # =================================================

    with col_control:


        callback = None


        if state:

            callback = state.get(
                "callback"
            )



        # ---------------------------------------------
        # EXISTING SESSION CLICKED
        # ---------------------------------------------

        if callback == "eventClick":


            click_data = state.get(
                "eventClick",
                {}
            )


            event_id = (

                click_data
                .get("event", {})
                .get("id")

            )


            selected_event = sessions[
                sessions["id"] == int(event_id)
            ]


            if len(selected_event) > 0:


                event = selected_event.iloc[0]


                st.subheader(
                    "Manage Session"
                )


                st.warning(
                    f"Selected: {event['student']}"
                )


                st.write(
                    f"📅 Date: {event['session_date']}"
                )


                st.write(
                    f"⏰ Time: {event['session_time']}"
                )


                if event["topic"]:

                    st.write(
                        f"Topic: {event['topic']}"
                    )


                if event["recurring_group"]:


                    st.info(
                        "This belongs to a recurring series."
                    )


                st.session_state.selected_session_id = int(
                    event["id"]
                )


                st.session_state.selected_group = (
                    event["recurring_group"]
                )

        # ---------------------------------------------
        # EMPTY DATE CLICKED
        # ---------------------------------------------

        elif callback == "dateClick":


            click_data = state.get(
                "dateClick",
                {}
            )


            raw_date = (

                click_data.get("dateStr")
                or click_data.get("date")
                or ""

            )


            clicked_date = raw_date.split("T")[0]


            st.session_state.calendar_date = clicked_date


            st.subheader(
                "➕ Create New Session"
            )


            st.info(
                f"Selected Date: {clicked_date}"
            )



            with st.form(
                "new_session_form"
            ):


                selected_student = st.selectbox(

                    "Student",

                    list(student_map.keys())

                )


                selected_time = st.selectbox(

                    "Start Time",

                    TIME_SLOTS

                )


                duration = st.selectbox(

                    "Duration",

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


                topic = st.text_input(
                    "Lesson Topic"
                )


                notes = st.text_area(
                    "Notes"
                )


                recurring = st.checkbox(

                    "Repeat weekly?"

                )


                weeks = 1


                if recurring:


                    weeks = st.number_input(

                        "Number of weeks",

                        min_value=2,

                        max_value=52,

                        value=4

                    )



                save = st.form_submit_button(

                    "Confirm Reservation",

                    use_container_width=True

                )



                if save:


                    group_id = (

                        str(uuid.uuid4())

                        if recurring

                        else None

                    )


                    start_date = datetime.strptime(

                        clicked_date,

                        "%Y-%m-%d"

                    ).date()



                    for i in range(

                        int(weeks)

                    ):


                        session_day = (

                            start_date
                            +
                            timedelta(
                                weeks=i
                            )

                        )


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

                                topic,

                                notes,

                                status

                            )


                            VALUES

                            (?,?,?,?,?,?,?,?,?)

                            """,

                            (

                                student_map[selected_student],

                                str(session_day),

                                selected_time,

                                duration,

                                "Weekly"
                                if recurring
                                else "None",

                                group_id,

                                topic,

                                notes,

                                "Scheduled"

                            )

                        )


                    st.success(

                        "Session(s) created successfully."

                    )


                    st.rerun()



        # ---------------------------------------------
        # NO CLICK
        # ---------------------------------------------

        else:


            st.subheader(
                "Interactive Console"
            )


            st.info(
                """
                • Click an empty calendar date to schedule a lesson.

                • Click an existing colored session to manage it.

                • Green sessions belong to recurring series.

                • Attendance will later be marked from completed sessions.
                """
            )



    # =================================================
    # DELETE / MODIFY SECTION
    # =================================================

    st.divider()


    if "selected_session_id" in st.session_state:


        st.subheader(
            "Remove Selected Session"
        )


        selected_id = st.session_state.selected_session_id


        group_id = st.session_state.get(
            "selected_group"
        )


        if group_id:


            delete_option = st.radio(

                "Delete option",

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

                group_id

                and

                delete_option ==
                "Delete entire recurring series"

            ):


                execute(

                    """

                    DELETE FROM sessions

                    WHERE recurring_group=?

                    """,

                    (

                        group_id,

                    )

                )


            else:


                execute(

                    """

                    DELETE FROM sessions

                    WHERE id=?

                    """,

                    (

                        selected_id,

                    )

                )


            st.success(
                "Session removed."
            )


            del st.session_state.selected_session_id


            if "selected_group" in st.session_state:

                del st.session_state.selected_group


            st.rerun()