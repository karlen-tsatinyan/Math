import streamlit as st

from database import query_dataframe
from utils.datetime_utils import today_str
import os
from config import UPLOAD_FOLDER

from database import (execute, query_dataframe)

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
            # Dashboard KPIs
            # ==========================

            homework_due = query_dataframe(

                """

                SELECT COUNT(*) AS total

                FROM homework

                WHERE

                    student_id=?

                    AND status='Assigned'

                    AND archived=0

                """,

                (

                    student_id,

                )

            )

            sessions=query_dataframe(

                """

                SELECT COUNT(*) AS total

                FROM sessions

                WHERE

                    student_id=?

                    AND session_date>=?

                """,

                (

                    student_id,

                    today_str()

                )

            )

            payments=query_dataframe(

                """

                SELECT

                COALESCE(SUM(amount),0) AS total

                FROM payments

                WHERE student_id=?

                """,

                (

                    student_id,

                )

            )

            c1,c2,c3=st.columns(3)

            c1.metric(

                "📚 Homework Due",

                int(homework_due.iloc[0]["total"])

            )

            c2.metric(

                "📅 Upcoming Sessions",

                int(sessions.iloc[0]["total"])

            )

            c3.metric(

                "💰 Payments Made",

                f"${payments.iloc[0]['total']:,.2f}"

            )
            st.divider()

            st.subheader("Upcoming Homework")



    # ==========================
    # HOMEWORK
    # ==========================


    elif option=="Homework":

        from modules.homework import student_homework

        def student_homework():

            student_id = st.session_state.user["student_id"]

            st.header("📚 My Homework")


            homework = query_dataframe(

                """
                SELECT

                    id,
                    title,
                    curriculum_topic,
                    assigned_date,
                    due_date,
                    priority,
                    file_path,
                    file_link,
                    comment,
                    teacher_feedback,
                    grade,
                    status

                FROM homework

                WHERE student_id=?

                ORDER BY due_date

                """,

                (
                    student_id,
                )

            )


            if len(homework)==0:

                st.info(
                    "No homework assigned."
                )

                return



            for _, row in homework.iterrows():


                with st.container(border=True):

                    st.subheader(
                        row["title"]
                    )


                    col1, col2 = st.columns(2)


                    with col1:

                        st.write(
                            "📘 Topic:",
                            row["curriculum_topic"]
                        )

                        st.write(
                            "📅 Assigned:",
                            row["assigned_date"]
                        )

                        st.write(
                            "⏰ Due:",
                            row["due_date"]
                        )


                    with col2:

                        st.write(
                            "Priority:",
                            row["priority"]
                        )

                        st.write(
                            "Status:",
                            row["status"]
                        )


                        if row["grade"]:

                            st.success(
                                f"Grade: {row['grade']}"
                            )


                    if row["comment"]:

                        st.info(
                            f"Teacher Instructions:\n{row['comment']}"
                        )


                    # -------------------------
                    # DOWNLOAD ASSIGNMENT
                    # -------------------------

                    if row["file_path"]:

                        if os.path.exists(row["file_path"]):

                            with open(
                                row["file_path"],
                                "rb"
                            ) as file:

                                st.download_button(

                                    label="📥 Download Assignment",

                                    data=file,

                                    file_name=os.path.basename(
                                        row["file_path"]
                                    ),

                                    key=f"download_{row['id']}"

                                )


                    if row["file_link"]:

                        st.link_button(

                            "🔗 Open Assignment Link",

                            row["file_link"]

                        )


                    # -------------------------
                    # STUDENT UPLOAD
                    # -------------------------

                    st.write("---")

                    upload = st.file_uploader(

                        "Upload Completed Homework",

                        type=[
                            "pdf",
                            "jpg",
                            "jpeg",
                            "png"
                        ],

                        key=f"upload_{row['id']}"

                    )


                    if st.button(

                        "Submit Homework",

                        key=f"submit_{row['id']}"

                    ):


                        if upload is not None:
                            

                            os.makedirs(
                                UPLOAD_FOLDER,
                                exist_ok=True
                            )

                            path = os.path.join(
                                UPLOAD_FOLDER,
                                "student_" + upload.name
                            )

                            with open(
                                path,
                                "wb"
                            ) as f:

                                f.write(
                                    upload.getbuffer()
                                )


                            execute(

                                """
                                UPDATE homework

                                SET

                                    file_path=?,

                                    status='Submitted',

                                    submitted_at=CURRENT_TIMESTAMP

                                WHERE id=?

                                AND student_id=?

                                """,

                                (
                                    path,

                                    int(row["id"]),

                                    student_id

                                )

                            )


                            st.success(
                                "Homework submitted."
                            )

                            st.rerun()


                        else:

                            st.warning(
                                "Please upload your completed homework first."
                            )



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