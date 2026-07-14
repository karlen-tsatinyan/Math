import streamlit as st

from database import query_dataframe, execute


ALL_TRACKS = [

"1st Grade General Math",
"2nd Grade General Math",
"3rd Grade General Math",
"4th Grade General Math",
"5th Grade General Math",

"6th Grade Pre-Algebra",
"7th Grade Algebra I",
"8th Grade Algebra II",

"6th Grade Geometry",
"7th Grade Geometry",
"8th Grade Geometry",

"9th Grade Pre-Calculus",
"10th Grade Calculus A",
"11th Grade Calculus BC",

"12th Grade Advanced Math / Stats",

"Trigonometry Module",

"SAT/ACT Test Prep"

]



def curriculum_management():


    st.header(
        "📚 Live Curriculum Board & Resource Vault"
    )


    st.caption(
        "Manage curriculum tracks, resources, and student academic pathways."
    )


    board_tab, resource_tab = st.tabs(
        [
            "📊 Curriculum Board",
            "📂 Resource Library"
        ]
    )


    # ================================
    # BOARD VIEW
    # ================================

    with board_tab:


        students = query_dataframe(
            """
            SELECT
                id,
                first_name || ' ' || last_name AS Student,
                grade,
                subject

            FROM students

            ORDER BY last_name
            """
        )


        if students.empty:

            st.info(
                "No students found."
            )

        else:


            for _, student in students.iterrows():

                with st.container(border=True):

                    st.subheader(
                        student["Student"]
                    )

                    st.write(
                        f"Grade: {student['grade']}"
                    )

                    st.write(
                        f"Subject: {student['subject']}"
                    )


                    track = st.selectbox(
                        "Curriculum Track",

                        ALL_TRACKS,

                        key=f"track_{student['id']}"
                    )


                    if st.button(
                        "View Materials",
                        key=f"view_{student['id']}"
                    ):


                        resources = query_dataframe(
                            """
                            SELECT
                                resource_title,
                                resource_type,
                                direct_url

                            FROM curriculum_resources

                            WHERE grade_track=?

                            """,
                            (track,)
                        )


                        if resources.empty:

                            st.warning(
                                "No curriculum resources assigned."
                            )

                        else:

                            for _, resource in resources.iterrows():

                                with st.container(border=True):

                                    st.markdown(
                                        f"### 📘 {resource['resource_title']}"
                                    )

                                    st.caption(
                                        f"Type: {resource['resource_type']}"
                                    )


                                    if resource["direct_url"]:

                                        st.link_button(
                                            "🔗 Open Resource",
                                            resource["direct_url"],
                                            use_container_width=True
                                        )



    # ================================
    # RESOURCE LIBRARY
    # ================================


    with resource_tab:


        st.subheader(
            "Add Curriculum Resource"
        )


        with st.form(
            "resource_form"
        ):


            track = st.selectbox(
                "Grade Track",
                ALL_TRACKS
            )


            title = st.text_input(
                "Resource Title"
            )


            resource_type = st.selectbox(
                "Type",
                [
                    "Google Drive",
                    "PDF",
                    "Worksheet",
                    "Video",
                    "Other"
                ]
            )


            url = st.text_input(
                "Resource URL"
            )


            comment = st.text_area(
                "Teacher Notes"
            )



            submit = st.form_submit_button(
                "Save Resource"
            )


            if submit:


                if not title:

                    st.error(
                        "Title required"
                    )


                else:


                    execute(

                        """
                        INSERT INTO curriculum_resources

                        (
                        grade_track,
                        resource_title,
                        resource_type,
                        direct_url,
                        teacher_comment
                        )

                        VALUES
                        (?,?,?,?,?)

                        """,

                        (
                        track,
                        title,
                        resource_type,
                        url,
                        comment
                        )

                    )


                    st.success(
                        "Resource added."
                    )

                    st.rerun()



        st.divider()


        st.subheader(
            "Curriculum Asset Index"
        )


        resources=query_dataframe(

            """
            SELECT

            grade_track,
            resource_title,
            resource_type,
            direct_url

            FROM curriculum_resources

            ORDER BY grade_track

            """

        )


        for _, resource in resources.iterrows():

            with st.expander(
                f"📂 {resource['grade_track']} - {resource['resource_title']}"
            ):

                st.write(
                    f"Category: {resource['resource_type']}"
                )


                if resource["direct_url"]:

                    st.link_button(
                        "Open Link",
                        resource["direct_url"]
                    )