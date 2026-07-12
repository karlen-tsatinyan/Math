import streamlit as st

from database import query_dataframe



def student_profile():

    st.title(
        "👨‍🎓 Student Profile"
    )


    students=query_dataframe(

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


        ORDER BY last_name


        """

    )


    if len(students)==0:

        st.warning(
            "No students found."
        )

        return



    selected=st.selectbox(

        "Select Student",

        students["name"]

    )



    student=students[

        students["name"]==selected

    ].iloc[0]



    # -------------------------
    # BASIC INFORMATION
    # -------------------------


    st.subheader(
        "Student Information"
    )


    col1,col2=st.columns(2)


    with col1:

        st.write(
            "Name:",
            student["name"]
        )

        st.write(
            "Grade:",
            student["grade"]
        )

        st.write(
            "Subject:",
            student["subject"]
        )


    with col2:

        st.write(
            "Email:",
            student["email"]
        )

        st.write(
            "Phone:",
            student["phone"]
        )



    st.divider()



    student_id=int(student["id"])

    # ===========================
    # STUDENT OVERVIEW
    # ===========================

    st.subheader("📊 Student Overview")

    # Total payments
    payment_total = query_dataframe(
        """
        SELECT
            COALESCE(SUM(amount),0) AS total
        FROM payments
        WHERE student_id=?
        """,
        (student_id,)
    )

    # Session count
    session_count = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM sessions
        WHERE student_id=?
        """,
        (student_id,)
    )

    # Attendance
    attendance_count = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM attendance
        WHERE student_id=?
        AND status='Present'
        """,
        (student_id,)
    )

    # Homework submitted
    homework_count = query_dataframe(
        """
        SELECT
            COUNT(*) AS total
        FROM homework
        WHERE student_id=?
        """,
        (student_id,)
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "💰 Payments",
        f"${payment_total.iloc[0]['total']:,.2f}"
    )

    col2.metric(
        "📅 Sessions",
        int(session_count.iloc[0]["total"])
    )

    col3.metric(
        "✅ Attendance",
        int(attendance_count.iloc[0]["total"])
    )

    col4.metric(
        "📚 Homework",
        int(homework_count.iloc[0]["total"])
    )

    st.divider()

    next_session = query_dataframe(
        """
        SELECT

            session_date,
            session_time,
            topic

        FROM sessions

        WHERE student_id=?
        AND session_date >= date('now')

        ORDER BY session_date, session_time

        LIMIT 1
        """,
        (student_id,)
    )

    if len(next_session) > 0:

        st.info(
            f"""
    **Next Lesson**

    📅 {next_session.iloc[0]['session_date']}

    🕒 {next_session.iloc[0]['session_time']}

    📖 {next_session.iloc[0]['topic']}
    """
        )

    latest_note = query_dataframe(
        """
        SELECT

            lesson_date,
            topic

        FROM progress_notes

        WHERE student_id=?

        ORDER BY lesson_date DESC

        LIMIT 1
        """,
        (student_id,)
    )

    if len(latest_note) > 0:

        st.success(
            f"""
    Latest Progress Note

    {latest_note.iloc[0]['lesson_date']}

    {latest_note.iloc[0]['topic']}
    """
        )

    st.subheader("⚡ Quick Actions")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        if st.button(
            "💰 Payment",
            use_container_width=True
        ):
            st.session_state.selected_student = student_id
            st.session_state.admin_option = "Payments"
            st.rerun()

    with c2:
        if st.button(
            "📚 Homework",
            use_container_width=True
        ):
            st.session_state.selected_student = student_id
            st.session_state.admin_option = "Homework"
            st.rerun()

    with c3:
        if st.button(
            "📅 Schedule",
            use_container_width=True
        ):
            st.session_state.selected_student = student_id
            st.session_state.admin_option = "Schedule"
            st.rerun()

    with c4:
        if st.button(
            "✅ Attendance",
            use_container_width=True
        ):
            st.session_state.selected_student = student_id
            st.session_state.admin_option = "Attendance"
            st.rerun()

    with c5:
        if st.button(
            "📝 Progress",
            use_container_width=True
        ):
            st.session_state.selected_student = student_id
            st.session_state.admin_option = "Progress Notes"
            st.rerun()


    # -------------------------
    # TABS
    # -------------------------


    tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "💰 Payments",

        "📚 Homework",

        "📅 Sessions",

        "✅ Attendance",

        "📝 Progress Notes"
    ]
)



    # PAYMENTS

    with tab1:


        payments=query_dataframe(

            """

            SELECT

            amount,

            payment_date,

            period


            FROM payments


            WHERE student_id=?


            ORDER BY payment_date DESC


            """,

            (

            student_id,

            )

        )


        if len(payments)==0:

            st.info(
                "No payments."
            )

        else:

            st.dataframe(

                payments,

                hide_index=True,

                use_container_width=True

            )



    # HOMEWORK

    with tab2:


        homework=query_dataframe(

            """

            SELECT

            status,

            comment,

            teacher_feedback,

            created_at


            FROM homework


            WHERE student_id=?


            ORDER BY created_at DESC


            """,

            (

            student_id,

            )

        )


        if len(homework)==0:

            st.info(
                "No homework."
            )

        else:

            st.dataframe(

                homework,

                hide_index=True,

                use_container_width=True

            )



    # SESSIONS

    with tab3:


        sessions=query_dataframe(

            """

            SELECT

            session_date,

            session_time,

            topic,

            notes


            FROM sessions


            WHERE student_id=?


            ORDER BY session_date DESC


            """,

            (

            student_id,

            )

        )


        if len(sessions)==0:

            st.info(
                "No sessions."
            )

        else:

            st.dataframe(

                sessions,

                hide_index=True,

                use_container_width=True

            )



    # ATTENDANCE

    with tab4:


        attendance=query_dataframe(

            """

            SELECT

            date,

            status


            FROM attendance


            WHERE student_id=?


            ORDER BY date DESC


            """,

            (

            student_id,

            )

        )


        if len(attendance)==0:

            st.info(
                "No attendance records."
            )

        else:

            st.dataframe(

                attendance,

                hide_index=True,

                use_container_width=True

            )
    # -------------------------
    # PROGRESS NOTES
    # -------------------------

    with tab5:

        notes = query_dataframe(
            """
            SELECT

                lesson_date,
                topic,
                strengths,
                improvements,
                homework,
                next_steps

            FROM progress_notes

            WHERE student_id=?

            ORDER BY lesson_date DESC
            """,
            (student_id,)
        )

        if len(notes) == 0:

            st.info("No progress notes yet.")

        else:

            for _, row in notes.iterrows():

                with st.expander(
                    f"{row['lesson_date']} - {row['topic']}"
                ):

                    st.markdown("**Strengths**")
                    st.write(row["strengths"])

                    st.markdown("**Needs Improvement**")
                    st.write(row["improvements"])

                    st.markdown("**Homework**")
                    st.write(row["homework"])

                    st.markdown("**Next Lesson**")
                    st.write(row["next_steps"])