import streamlit as st

from database import query_dataframe



def student_page():


    student_id = (
        st.session_state.user["student_id"]
    )


    st.sidebar.title(
        "Student Portal"
    )


    option=st.sidebar.radio(

        "Menu",

        [

            "Dashboard",

            "Homework",

            "Schedule",

            "Payments"

        ]

    )


    # ==========================
    # DASHBOARD
    # ==========================


    if option=="Dashboard":


        st.title(
            "Student Dashboard"
        )


        student=query_dataframe(

            """

            SELECT

            first_name,

            last_name,

            grade,

            subject


            FROM students


            WHERE id=?

            """,

            (

            student_id,

            )

        )


        if len(student)>0:


            row=student.iloc[0]


            st.success(

                f"""
                Welcome {row['first_name']} {row['last_name']}

                Grade: {row['grade']}

                Subject: {row['subject']}
                """

            )



    # ==========================
    # HOMEWORK
    # ==========================


    elif option=="Homework":

        from modules.homework import student_homework

        student_homework()



    # ==========================
    # SCHEDULE
    # ==========================


    elif option=="Schedule":


        st.title(

            "My Sessions"

        )


        sessions=query_dataframe(

            """

            SELECT

            session_date,

            session_time,

            topic,

            notes


            FROM sessions


            WHERE student_id=?


            ORDER BY session_date


            """,

            (

            student_id,

            )

        )


        st.dataframe(

            sessions,

            use_container_width=True

        )



        zoom=query_dataframe(

            """

            SELECT

            zoom_link,

            meeting_id


            FROM students


            WHERE id=?


            """,

            (

            student_id,

            )

        )


        if len(zoom)>0:


            st.info(

                f"""

                Zoom Link:

                {zoom.iloc[0]['zoom_link']}


                Meeting ID:

                {zoom.iloc[0]['meeting_id']}

                """

            )



    # ==========================
    # PAYMENTS
    # ==========================


    elif option=="Payments":


        st.title(

            "Payment History"

        )


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


        st.dataframe(

            payments,

            use_container_width=True

        )