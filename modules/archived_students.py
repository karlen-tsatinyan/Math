import streamlit as st

from database import execute, query_dataframe


def archived_students():

    st.header("🗄 Archived Students")

    st.caption(
        "Archived students are hidden from the active student list "
        "but their academic and financial history remains preserved."
    )

    students = query_dataframe(
        """
        SELECT
            id,
            student_code,
            first_name,
            last_name,
            grade,
            subject,
            email,
            phone
        FROM students
        WHERE COALESCE(archived, 0) = 1
        ORDER BY last_name, first_name
        """
    )

    if students.empty:
        st.info("No archived students found.")
        return

    students["Student Name"] = (
        students["first_name"].fillna("")
        + " "
        + students["last_name"].fillna("")
    ).str.strip()

    display_df = students[
        [
            "id",
            "student_code",
            "Student Name",
            "grade",
            "subject",
            "email",
            "phone",
        ]
    ].rename(
        columns={
            "id": "ID",
            "student_code": "Student Code",
            "grade": "Grade",
            "subject": "Subject",
            "email": "Email",
            "phone": "Phone",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    options = {}

    for _, row in students.iterrows():

        label = (
            f"{row['Student Name']} "
            f"(ID: {row['id']})"
        )

        options[label] = int(row["id"])

    selected_label = st.selectbox(
        "Select Archived Student",
        list(options.keys()),
        key="archived_student_select"
    )

    selected_id = options[selected_label]

    selected = students[
        students["id"] == selected_id
    ].iloc[0]

    st.subheader(
        f"👤 {selected['Student Name']}"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Student ID",
        selected_id
    )

    col2.metric(
        "Grade",
        selected["grade"] or "—"
    )

    col3.metric(
        "Subject",
        selected["subject"] or "—"
    )

    st.write(
        f"**Email:** {selected['email'] or '—'}"
    )

    st.write(
        f"**Phone:** {selected['phone'] or '—'}"
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "♻️ Restore Student",
            key=f"restore_student_{selected_id}",
            use_container_width=True
        ):

            execute(
                """
                UPDATE students
                SET archived = 0
                WHERE id = %s
                """,
                (selected_id,)
            )

            st.cache_data.clear()

            st.success(
                "Student restored successfully."
            )

            st.rerun()

    with col2:

        st.warning(
            "Permanent deletion should be handled carefully "
            "because the student may have homework, payments, "
            "attendance, and session history."
        )
