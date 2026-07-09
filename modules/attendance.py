import streamlit as st

from datetime import date

from database import (
    execute,
    query_dataframe
)



def attendance_management():

    st.header(
        "Attendance Tracking"
    )


    sessions=query_dataframe(

        """

        SELECT

        sessions.id,

        students.first_name || ' ' ||

        students.last_name AS Student,


        session_date,

        session_time


        FROM sessions


        JOIN students

        ON sessions.student_id=students.id


        ORDER BY session_date


        """

    )


    if len(sessions)==0:

        st.info(
            "No sessions scheduled."
        )

        return



    session_id=st.selectbox(

        "Select Session",

        sessions["id"],

        format_func=lambda x:

        sessions[
            sessions["id"]==x
        ]["Student"].iloc[0]

    )


    status=st.selectbox(

        "Attendance Status",

        [

            "Present",

            "Absent",

            "Cancelled"

        ]

    )


    if st.button(

        "Save Attendance"

    ):


        student_id=int(

            query_dataframe(

                """

                SELECT student_id

                FROM sessions

                WHERE id=?

                """,

                (

                    session_id,

                )

            ).iloc[0]["student_id"]

        )


        execute(

            """

            INSERT INTO attendance

            (

            student_id,

            session_id,

            status,

            date

            )

            VALUES

            (?,?,?,?)

            """,

            (

                student_id,

                session_id,

                status,

                str(date.today())

            )

        )


        st.success(

            "Attendance saved."

        )



    st.subheader(

        "Attendance History"

    )


    history=query_dataframe(

        """

        SELECT

        students.first_name || ' ' ||

        students.last_name AS Student,


        attendance.status,

        attendance.date


        FROM attendance


        JOIN students

        ON attendance.student_id=students.id


        ORDER BY attendance.date DESC


        """

    )


    st.dataframe(

        history,

        use_container_width=True

    )