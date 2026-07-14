import streamlit as st
import os
from datetime import date

from database import (
    execute,
    query_dataframe
)

from config import UPLOAD_FOLDER



# ==========================================
# ADMIN HOMEWORK MANAGEMENT
# ==========================================

def homework_management():


    st.header(
        "Teacher Homework Management"
    )


    tab1, tab2 = st.tabs(
        [
            "Assign Homework",
            "Review Submissions"
        ]
    )


    students=query_dataframe(

        """
        SELECT

        id,

        first_name || ' ' || last_name AS name

        FROM students

        ORDER BY last_name

        """

    )


    if len(students)==0:

        st.warning(
            "No students available."
        )

        return
    
    # Remember selected student

    selected_student_id = st.session_state.get("selected_student")

    student_names = students["name"].tolist()

    default_index = 0

    if selected_student_id is not None:

        match = students[
            students["id"] == selected_student_id
        ]

        if len(match) > 0:

            default_index = match.index[0]



    # --------------------------------------
    # ASSIGN HOMEWORK
    # --------------------------------------

    with tab1:

        student_name = st.selectbox(

            "Student",

            student_names,

            index=default_index,

            key="assign_student"

        )

        student_id=int(

            students[
                students["name"]==student_name
            ]["id"].iloc[0]

        )
        st.session_state.selected_student = student_id
        

        uploaded_file=st.file_uploader(

            "Upload Assignment",

            type=[
                "pdf",
                "jpg",
                "jpeg",
                "png"
            ],

            key="teacher_upload"

        )


        drive_link=st.text_input(

            "Google Drive Link"

        )


        comment=st.text_area(

            "Instructions"

        )



        if st.button(

            "Assign Homework"

        ):


            file_path=None


            if uploaded_file:


                file_path=os.path.join(

                    UPLOAD_FOLDER,

                    uploaded_file.name

                )


                with open(

                    file_path,

                    "wb"

                ) as f:

                    f.write(

                        uploaded_file.getbuffer()

                    )



            execute(

                """

                INSERT INTO homework

                (

                student_id,

                uploaded_by,

                file_path,

                file_link,

                comment,

                status

                )


                VALUES

                (?,?,?,?,?,?)

                """,

                (

                student_id,

                "admin",

                file_path,

                drive_link,

                comment,

                "Assigned"

                )

            )


            st.success(

                "Homework assigned."

            )



    # --------------------------------------
    # REVIEW STUDENT WORK
    # --------------------------------------

    with tab2:


        submissions=query_dataframe(

            """

            SELECT


            h.id,


            s.first_name || ' ' ||

            s.last_name AS Student,


            h.file_path,


            h.file_link,


            h.status,


            h.teacher_feedback,


            h.created_at


            FROM homework h


            JOIN students s


            ON h.student_id=s.id


            ORDER BY h.created_at DESC


            """

        )



        st.dataframe(

            submissions,

            use_container_width=True

        )



        if len(submissions)>0:


            selected_id=st.selectbox(

                "Homework ID",

                submissions["id"]

            )


            feedback=st.text_area(

                "Teacher Feedback"

            )

            score = st.number_input(
                "Score",
                min_value=0.0,
                step=1.0
            )

            max_score = st.number_input(
                "Maximum Score",
                min_value=1.0,
                value=20.0,
                step=1.0
            )

            topic = st.text_input(
                "Topic",
                placeholder="Quadratic Equations"
            )

            if st.button(

                "Save Feedback"

            ):
                
                percent = round(score / max_score * 100, 1)

                if percent >= 97:
                    letter = "A+"
                elif percent >= 93:
                    letter = "A"
                elif percent >= 90:
                    letter = "A-"
                elif percent >= 87:
                    letter = "B+"
                elif percent >= 83:
                    letter = "B"
                elif percent >= 80:
                    letter = "B-"
                elif percent >= 77:
                    letter = "C+"
                elif percent >= 73:
                    letter = "C"
                elif percent >= 70:
                    letter = "C-"
                elif percent >= 60:
                    letter = "D"
                else:
                    letter = "F"

                execute(

                    """

                    UPDATE homework

                    SET

                    teacher_feedback=?,

                    status='Reviewed'


                    WHERE id=?

                    """,

                    (

                    feedback,

                    int(selected_id)

                    )

                )


                st.success(

                    "Feedback saved."

                )

                student = query_dataframe(
                    """
                    SELECT student_id
                    FROM homework
                    WHERE id=?
                    """,
                    (int(selected_id),)
                )

                student_id = int(student.iloc[0]["student_id"])

                execute(
                    """
                    INSERT INTO homework_grades
                    (
                        homework_id,
                        student_id,
                        lesson_date,
                        topic,
                        score,
                        max_score,
                        percent,
                        grade_letter,
                        teacher_comment
                    )
                    VALUES
                    (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        int(selected_id),
                        student_id,
                        str(date.today()),
                        topic,
                        score,
                        max_score,
                        percent,
                        letter,
                        feedback
                    )
                )





# ==========================================
# STUDENT HOMEWORK PORTAL
# ==========================================


def student_homework():


    student_id=(

        st.session_state.user["student_id"]

    )


    st.header(

        "My Homework"

    )



    homework=query_dataframe(

        """

        SELECT


        id,

        file_path,

        file_link,

        comment,

        teacher_feedback,

        status,

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

            "No homework assigned."

        )

        return



    for index,row in homework.iterrows():


        st.subheader(

            f"Assignment #{row['id']}"

        )


        st.write(

            "Instructions:",

            row["comment"]

        )


        st.write(

            "Status:",

            row["status"]

        )


        if row["file_link"]:

            st.markdown(

                row["file_link"]

            )


        if row["teacher_feedback"]:

            st.success(

                "Teacher Feedback: "

                +

                row["teacher_feedback"]

            )


        st.divider()



    # ------------------------------
    # STUDENT UPLOAD
    # ------------------------------


    st.subheader(

        "Submit Completed Homework"

    )


    upload=st.file_uploader(

        "Upload Your Solution",

        type=[

            "pdf",

            "jpg",

            "jpeg",

            "png"

        ]

    )


    selected_assignment=st.selectbox(

        "Assignment ID",

        homework["id"]

    )



    if st.button(

        "Submit Homework"

    ):


        if upload:


            path=os.path.join(

                UPLOAD_FOLDER,

                "student_"

                +

                upload.name

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

                status='Submitted'


                WHERE id=?

                AND student_id=?

                """,

                (

                path,

                int(selected_assignment),

                student_id

                )

            )


            st.success(

                "Homework submitted."

            )