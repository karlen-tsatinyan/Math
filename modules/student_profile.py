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



    # -------------------------
    # TABS
    # -------------------------


    tab1,tab2,tab3,tab4 = st.tabs(

        [

            "💰 Payments",

            "📚 Homework",

            "📅 Sessions",

            "✅ Attendance"

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