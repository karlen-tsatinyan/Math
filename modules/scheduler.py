import streamlit as st

from datetime import date

from database import (
    execute,
    query_dataframe
)



TIME_SLOTS = [

    "8:00 AM",
    "9:00 AM",
    "10:00 AM",
    "11:00 AM",
    "12:00 PM",
    "1:00 PM",
    "2:00 PM",
    "3:00 PM",
    "4:00 PM",
    "5:00 PM",
    "6:00 PM",
    "7:00 PM"

]



def scheduler_management():


    st.header(
        "Tutoring Session Scheduler"
    )



    students=query_dataframe(

        """

        SELECT

        id,

        first_name || ' ' || last_name AS name,

        zoom_link,

        meeting_id


        FROM students


        ORDER BY last_name


        """

    )


    if len(students)==0:

        st.warning(
            "No students found."
        )

        return



    tab1,tab2,tab3 = st.tabs(

        [

            "Reserve Session",

            "Calendar View",

            "Remove Session"

        ]

    )



    # ======================================
    # RESERVE SESSION
    # ======================================

    with tab1:


        student_name=st.selectbox(

            "Student",

            students["name"],

            key="calendar_student"

        )


        student=students[

            students["name"]==student_name

        ].iloc[0]



        st.info(

            f"""

Zoom Link:

{student['zoom_link']}


Meeting ID:

{student['meeting_id']}

            """

        )



        session_date=st.date_input(

            "Session Date",

            value=date.today()

        )


        session_time=st.selectbox(

            "Time Slot",

            TIME_SLOTS

        )


        topic=st.text_input(

            "Lesson Topic"

        )


        notes=st.text_area(

            "Notes"

        )



        # Check availability

        conflict=query_dataframe(

            """

            SELECT *

            FROM sessions


            WHERE session_date=?

            AND session_time=?

            """,

            (

            str(session_date),

            session_time

            )

        )



        if len(conflict)>0:


            st.warning(

                "This time slot is already reserved."

            )


        else:


            if st.button(

                "Reserve Session"

            ):


                execute(

                    """

                    INSERT INTO sessions

                    (

                    student_id,

                    session_date,

                    session_time,

                    topic,

                    notes

                    )


                    VALUES

                    (?,?,?,?,?)

                    """,

                    (

                    int(student["id"]),

                    str(session_date),

                    session_time,

                    topic,

                    notes

                    )

                )


                st.success(

                    "Session scheduled."

                )



    # ======================================
    # CALENDAR VIEW
    # ======================================


    with tab2:


        st.subheader(

            "Upcoming Sessions"

        )


        sessions=query_dataframe(

            """

            SELECT


            sessions.id,


            students.first_name ||

            ' ' ||

            students.last_name AS Student,


            session_date AS Date,


            session_time AS Time,


            topic


            FROM sessions


            JOIN students


            ON sessions.student_id=students.id


            ORDER BY session_date, session_time


            """

        )



        if len(sessions)>0:


            st.dataframe(

                sessions,

                use_container_width=True

            )


        else:

            st.info(

                "No sessions scheduled."

            )



    # ======================================
    # DELETE
    # ======================================


    with tab3:


        sessions=query_dataframe(

            """

            SELECT


            sessions.id,


            students.first_name ||

            ' ' ||

            students.last_name AS Student,


            session_date,


            session_time


            FROM sessions


            JOIN students


            ON sessions.student_id=students.id


            ORDER BY session_date


            """

        )



        if len(sessions)>0:


            session_id=st.selectbox(

                "Session ID",

                sessions["id"]

            )


            if st.button(

                "Delete Session"

            ):


                execute(

                    """

                    DELETE FROM sessions

                    WHERE id=?

                    """,

                    (

                    int(session_id),

                    )

                )


                st.success(

                    "Session removed."

                )


                st.rerun()