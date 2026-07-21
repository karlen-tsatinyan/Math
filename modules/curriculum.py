import os
import streamlit as st

from database import query_dataframe, execute
from config import UPLOAD_FOLDER

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


def sanitize_url(url: str) -> str:
    """Ensure URLs have a valid protocol for st.link_button."""
    if not url:
        return ""
    clean_url = url.strip()
    if clean_url and not clean_url.startswith(("http://", "https://")):
        return f"https://{clean_url}"
    return clean_url


def curriculum_management():
    st.header("📚 Live Curriculum Board & Resource Vault")
    st.caption("Manage curriculum tracks, resources, and student academic pathways.")

    board_tab, resource_tab = st.tabs(
        [
            "📊 Curriculum Board",
            "📂 Resource Library"
        ]
    )

    # ==========================================
    # TAB 1: CURRICULUM BOARD
    # ==========================================
    with board_tab:
        students = query_dataframe(
            """
            SELECT
                id,
                first_name || ' ' || last_name AS student_name,
                grade,
                subject,
                COALESCE(curriculum_track, '1st Grade General Math') AS current_track
            FROM students
            ORDER BY last_name, first_name
            """
        )

        if students.empty:
            st.info("No students found in system.")
        else:
            for _, student in students.iterrows():
                student_id = int(student["id"])
                
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.subheader(f"👤 {student['student_name']}")
                        st.write(f"**Grade:** {student['grade'] or 'N/A'}")
                        st.write(f"**Subject:** {student['subject'] or 'N/A'}")

                    with col2:
                        current_track = student["current_track"]
                        default_index = ALL_TRACKS.index(current_track) if current_track in ALL_TRACKS else 0

                        selected_track = st.selectbox(
                            "Curriculum Track",
                            ALL_TRACKS,
                            index=default_index,
                            key=f"track_select_{student_id}"
                        )

                        if st.button("💾 Save Track Update", key=f"save_track_{student_id}"):
                            execute(
                                """
                                UPDATE students
                                SET curriculum_track = ?
                                WHERE id = ?
                                """,
                                (selected_track, student_id)
                            )
                            st.success(f"Updated track to '{selected_track}'!")
                            st.rerun()

                    # Material Viewer Expander
                    with st.expander(f"📖 View Assigned Materials for {selected_track}"):
                        resources = query_dataframe(
                            """
                            SELECT
                                id,
                                resource_title,
                                resource_type,
                                direct_url,
                                file_path,
                                teacher_comment
                            FROM curriculum_resources
                            WHERE grade_track = ?
                            ORDER BY id DESC
                            """,
                            (selected_track,)
                        )

                        if resources.empty:
                            st.caption("No resources linked to this curriculum track yet.")
                        else:
                            for _, res in resources.iterrows():
                                st.markdown(f"#### 📘 {res['resource_title']}")
                                st.caption(f"**Type:** {res['resource_type']}")

                                if res["teacher_comment"]:
                                    st.info(f"**Notes:** {res['teacher_comment']}")

                                col_btn1, col_btn2 = st.columns(2)

                                if res["direct_url"]:
                                    with col_btn1:
                                        st.link_button(
                                            "🔗 Open Resource Link",
                                            res["direct_url"],
                                            use_container_width=True
                                        )

                                if res["file_path"] and os.path.exists(res["file_path"]):
                                    with col_btn2:
                                        with open(res["file_path"], "rb") as f:
                                            st.download_button(
                                                "📥 Download Document",
                                                f,
                                                file_name=os.path.basename(res["file_path"]),
                                                key=f"dl_board_{student_id}_{res['id']}",
                                                use_container_width=True
                                            )

    # ==========================================
    # TAB 2: RESOURCE LIBRARY
    # ==========================================
    with resource_tab:
        st.subheader("Add Curriculum Resource")

        with st.form("resource_form", clear_on_submit=True):
            track = st.selectbox("Grade Track", ALL_TRACKS)
            title = st.text_input("Resource Title", placeholder="e.g., Polynomial Long Division Worksheet")

            resource_type = st.selectbox(
                "Type",
                ["Worksheet", "PDF Document", "Google Drive", "Video Lesson", "External Website", "Other"]
            )

            uploaded_file = st.file_uploader(
                "Upload File (Optional)",
                type=["pdf", "png", "jpg", "docx", "xlsx"],
                key="curriculum_file_upload"
            )

            url = st.text_input("Resource URL (Optional)", placeholder="https://drive.google.com/...")
            comment = st.text_area("Teacher Notes & Instructions")

            submit = st.form_submit_button("➕ Save Resource to Vault", type="primary")

            if submit:
                if not title.strip():
                    st.error("Please enter a resource title.")
                else:
                    saved_file_path = None
                    cleaned_url = sanitize_url(url)

                    # Handle File Saving
                    if uploaded_file:
                        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                        safe_filename = f"curriculum_{track.replace(' ', '_')}_{uploaded_file.name}"
                        saved_file_path = os.path.join(UPLOAD_FOLDER, safe_filename)

                        with open(saved_file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    execute(
                        """
                        INSERT INTO curriculum_resources (
                            grade_track,
                            resource_title,
                            resource_type,
                            direct_url,
                            file_path,
                            teacher_comment
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            track,
                            title.strip(),
                            resource_type,
                            cleaned_url if cleaned_url else None,
                            saved_file_path,
                            comment.strip() if comment else None
                        )
                    )

                    st.success(f"Resource '{title.strip()}' saved to {track}!")
                    st.rerun()

        st.divider()

        # Vault Asset Index
        st.subheader("Curriculum Asset Index")

        resources = query_dataframe(
            """
            SELECT
                id,
                grade_track,
                resource_title,
                resource_type,
                direct_url,
                file_path,
                teacher_comment
            FROM curriculum_resources
            ORDER BY grade_track, resource_title
            """
        )

        if resources.empty:
            st.info("No curriculum resources available in the library.")
        else:
            for _, res in resources.iterrows():
                res_id = int(res["id"])

                with st.expander(f"📂 [{res['grade_track']}] {res['resource_title']}"):
                    st.write(f"**Type:** {res['resource_type']}")

                    if res["teacher_comment"]:
                        st.caption(f"**Teacher Notes:** {res['teacher_comment']}")

                    col_a, col_b, col_c = st.columns([2, 2, 1])

                    with col_a:
                        if res["direct_url"]:
                            st.link_button("🔗 Open Web Link", res["direct_url"])

                    with col_b:
                        if res["file_path"] and os.path.exists(res["file_path"]):
                            with open(res["file_path"], "rb") as f:
                                st.download_button(
                                    "📥 Download PDF",
                                    f,
                                    file_name=os.path.basename(res["file_path"]),
                                    key=f"vault_dl_{res_id}"
                                )

                    with col_c:
                        if st.button("🗑️ Delete", key=f"del_res_{res_id}"):
                            # Clean up disk space if local file exists
                            if res["file_path"] and os.path.exists(res["file_path"]):
                                try:
                                    os.remove(res["file_path"])
                                except OSError:
                                    pass

                            execute("DELETE FROM curriculum_resources WHERE id = ?", (res_id,))
                            st.success("Resource removed.")
                            st.rerun()
