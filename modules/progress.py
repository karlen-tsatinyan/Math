import streamlit as st

from database import execute, query_dataframe



def progress_management():


    st.title(
        "📈 Student Progress Notes"
    )


    students=query_dataframe("""

    SELECT

    id,

    first_name || ' ' || last_name AS name


    FROM students


    ORDER BY last_name


    """)


    if len(students)==0:

        st.warning(
            "No students."
        )

        return



    student_name=st.selectbox(

        "Student",

        students["name"]

    )


    student_id=int(

        students[
            students["name"]==student_name
        ]["id"].iloc[0]

    )



    tab1,tab2 = st.tabs(

        [

            "➕ Add Note",

            "📖 View History"

        ]

    )



    # ------------------------
    # ADD NOTE
    # ------------------------

    with tab1:


        lesson_date=st.date_input(
            "Lesson Date"
        )


        topic=st.text_input(
            "Lesson Topic"
        )


        strengths=st.text_area(
            "Strengths"
        )


        improvements=st.text_area(
            "Needs Improvement"
        )


        homework=st.text_area(
            "Homework"
        )


        next_steps=st.text_area(
            "Next Lesson"
        )



        if st.button(
            "Save Progress Note"
        ):


            execute(

                """

                INSERT INTO progress_notes

                (

                student_id,

                lesson_date,

                topic,

                strengths,

                improvements,

                homework,

                next_steps

                )


                VALUES

                (?,?,?,?,?,?,?)

                """,

                (

                student_id,

                str(lesson_date),

                topic,

                strengths,

                improvements,

                homework,

                next_steps

                )

            )


            st.success(
                "Progress saved."
            )



    # ------------------------
    # HISTORY
    # ------------------------

    with tab2:


        notes=query_dataframe(

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

            (

            student_id,

            )

        )


        if len(notes)==0:

            st.info(
                "No progress notes."
            )

        else:

            st.dataframe(

                notes,

                use_container_width=True,

                hide_index=True

            )