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
        
        title = st.text_input(
            "Homework Title"
        )

        curriculum = st.text_input(
            "Curriculum Topic"
        )

        assigned_date = st.date_input(
            "Assigned Date"
        )

        due_date = st.date_input(
            "Due Date"
        )

        priority = st.selectbox(
            "Priority",
            [
                "Normal",
                "Important"
            ]
        )

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


            assignment_file = None

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )


            if uploaded_file:


                filename = (
                    f"{student_id}_{date.today()}_{uploaded_file.name}"
                )

                assignment_file = os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )


                with open(

                    assignment_file,

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

                    title,

                    curriculum_topic,

                    assigned_date,

                    due_date,

                    priority,

                    assignment_file,

                    file_link,

                    comment,

                    status

                )

                VALUES

                (?,?,?,?,?,?,?,?,?,?,?)

                """,

                (

                    student_id,

                    "admin",

                    title,

                    curriculum,

                    str(assigned_date),

                    str(due_date),

                    priority,

                    assignment_file,

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

            h.title,

            s.first_name || ' ' ||

            s.last_name AS Student,

            h.assignment_file,

            h.student_file,

            h.file_link,

            h.status,

            h.teacher_feedback,

            COALESCE(h.grade,'') AS grade,

            datetime(h.created_at, 'localtime') AS created_at


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


            selected_id = st.selectbox(

                "Homework",

                submissions["id"],

                format_func=lambda x:

                    f"{submissions[submissions['id']==x].iloc[0]['Student']}"

                    +

                    " — "

                    +

                    (

                        submissions[submissions["id"]==x].iloc[0]["title"]

                        if submissions[submissions["id"]==x].iloc[0]["title"]

                        else f"Homework #{x}"

                    )

            )

            
            selected = submissions[
                submissions["id"] == selected_id
            ].iloc[0]

            st.info(

                f"""

            Student:
            {selected['Student']}

            Homework:
            {selected['title']}

            Current Status:
            {selected['status']}

            """

            )

            grade_options = [

                "",
                "A+",
                "A",
                "A-",
                "B+",
                "B",
                "B-",
                "C+",
                "C",
                "C-",
                "D",
                "F"

            ]


            current_grade = selected["grade"]

            if current_grade != current_grade:   # checks NaN
                current_grade = ""

            if current_grade not in grade_options:
                current_grade = ""


            grade = st.selectbox(

                "Letter Grade",

                grade_options,

                index=grade_options.index(current_grade)

            )

            feedback = st.text_area(

                "Teacher Feedback",

                value=selected["teacher_feedback"]

                if selected["teacher_feedback"]

                else ""

            )

            st.divider()

            st.subheader("Storage Management")

            if selected["assignment_file"]:

                st.success("Assignment PDF exists")

                if st.button(

                    "🗑 Delete Assignment PDF",

                    key="delete_assignment"

                ):

                    try:

                        os.remove(

                            selected["assignment_file"]

                        )

                    except FileNotFoundError:

                        pass

                    execute(

                        """

                        UPDATE homework

                        SET

                        assignment_file=NULL,

                        deleted_assignment_file=1

                        WHERE id=?

                        """,

                        (

                            int(selected_id),

                        )

                    )

                    st.success(

                        "Assignment PDF deleted."

                    )

                    st.rerun()


            if selected["student_file"]:

                st.success("Student submission exists")

                if st.button(

                    "🗑 Delete Student Submission",

                    key="delete_student"

                ):

                    try:

                        os.remove(

                            selected["student_file"]

                        )

                    except FileNotFoundError:

                        pass

                    execute(

                        """

                        UPDATE homework

                        SET

                        student_file=NULL,

                        deleted_student_file=1

                        WHERE id=?

                        """,

                        (

                            int(selected_id),

                        )

                    )

                    st.success(

                        "Student submission deleted."

                    )

                    st.rerun()        


            if st.button(

                "Save Feedback"

            ):
                
                
                execute(

                    """

                    UPDATE homework

                    SET

                    teacher_feedback=?,

                    grade=?,

                    status='Reviewed',

                    reviewed_at=CURRENT_TIMESTAMP

                    WHERE id=?

                    """,

                    (

                    feedback,

                    grade,

                    int(selected_id)

                    )

                )


                st.success(

                    "Feedback saved."

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

        title,

        curriculum_topic,

        assigned_date,

        due_date,

        priority,

        assignment_file,

        student_file,

        file_link,

        comment,

        teacher_feedback,

        grade,

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

        with st.container(border=True):


            st.subheader(row["title"] or f"Homework #{row['id']}")

            col1, col2 = st.columns(2)

            with col1:

                st.write("📚 Topic:", row["curriculum_topic"])

                st.write("📅 Assigned:", row["assigned_date"])

                st.write("⏰ Due:", row["due_date"])

            with col2:

                st.write("Priority:", row["priority"])

                if row["status"] == "Assigned":

                    st.warning("🟡 Waiting for submission")

                elif row["status"] == "Submitted":

                    st.info("🔵 Submitted - Waiting for grading")

                elif row["status"] == "Reviewed":

                    st.success("🟢 Graded")

                else:

                    st.write(row["status"])

                if row["grade"]:

                    st.success(f"Grade: {row['grade']}")

            st.write("Instructions")

            st.info(row["comment"])

            if row["assignment_file"]:

                with open(

                    row["assignment_file"],

                    "rb"

                ) as f:

                    st.download_button(

                        "📥 Download Assignment",

                        f,

                        file_name=os.path.basename(

                            row["assignment_file"]

                        )

                    )

            if row["file_link"]:

                st.link_button(
                    "🔗 Open Assignment Link",
                    row["file_link"]
                )


            if row["teacher_feedback"]:

                st.success(
                    row["teacher_feedback"]
                )

            if row["student_file"]:

                st.success(

                    "✅ Homework submitted."

                )

            else:

                st.warning(

                    "⌛ Awaiting submission."

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


    selected_assignment = st.selectbox(

        "Homework",

        homework["id"],

        format_func=lambda x:

            homework[
                homework["id"]==x
            ].iloc[0]["title"]

            if homework[
                homework["id"]==x
            ].iloc[0]["title"]

            else f"Homework #{x}"

    )



    if st.button(

        "Submit Homework"

    ):


        if upload:


            filename=(

                f"student_{student_id}_{selected_assignment}_{upload.name}"

            )

            student_file=os.path.join(

                UPLOAD_FOLDER,

                filename

            )


            with open(

                student_file,

                "wb"

            ) as f:


                f.write(

                    upload.getbuffer()

                )



            execute(

                """

                UPDATE homework

                SET

                student_file=?,

                status='Submitted',

                submitted_at=CURRENT_TIMESTAMP

                WHERE id=?

                AND student_id=?

                """,

                (

                student_file,

                int(selected_assignment),

                student_id

                )

            )


            st.success(

                "Homework submitted."

            )
            st.rerun()