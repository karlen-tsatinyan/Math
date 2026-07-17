import streamlit as st

from datetime import date

from database import (execute, query_dataframe)



def attendance_management():

    st.header(
        "Attendance History"
    )
    st.caption("Attendance is recorded from Student Profile → Sessions.")

    history = query_dataframe(
        """
        SELECT
            students.first_name || ' ' || students.last_name AS Student,
            attendance.session_date,
            attendance.session_time,
            attendance.status,
            attendance.marked_at

        FROM attendance

        JOIN students
        ON attendance.student_id = students.id

        ORDER BY
            attendance.session_date DESC,
            attendance.session_time DESC
        """
    )

    st.dataframe(

        history,

        use_container_width=True

    )