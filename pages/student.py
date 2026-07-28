import streamlit as st
from utils.datetime_utils import today_str
from database import execute, query_dataframe


def ensure_student_portal_schema():
    """Safely ensure essential columns exist in PostgreSQL."""
    columns_to_add = [
        ("students", "first_name", "TEXT DEFAULT ''"),
        ("students", "last_name", "TEXT DEFAULT ''"),
        ("students", "grade", "TEXT DEFAULT 'N/A'"),
        ("students", "subject", "TEXT DEFAULT 'N/A'"),
        ("students", "zoom_link", "TEXT"),
        ("students", "meeting_id", "TEXT"),
        ("sessions", "zoom_link", "TEXT"),
        ("homework", "archived", "INTEGER DEFAULT 0"),
        ("homework", "status", "TEXT DEFAULT 'Assigned'"),
        ("payments", "period", "TEXT"),
        ("payments", "payment_date", "DATE DEFAULT CURRENT_DATE"),
        ("payments", "amount", "NUMERIC DEFAULT 0.00"),
    ]

    for table_name, col_name, col_type in columns_to_add:
        try:
            execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
        except Exception:
            pass


@st.cache_data
def get_student_portal_data(student_id, today_date):
    """Fetches all student portal information with caching to eliminate lag."""
    
    # 1. Student Info
    student_df = query_dataframe(
        """
        SELECT 
            id,
            COALESCE(first_name, '') AS first_name,
            COALESCE(last_name, '') AS last_name,
            COALESCE(grade, 'N/A') AS grade,
            COALESCE(subject, 'N/A') AS subject,
            zoom_link,
            meeting_id
        FROM students
        WHERE id = %s
        """,
        (student_id,)
    )

    # 2. Homework Due Count
    homework_due = query_dataframe(
        """
        SELECT COUNT(*) AS total 
        FROM homework 
        WHERE student_id = %s AND status = 'Assigned' AND archived = 0
        """,
        (student_id,)
    )

    # 3. Upcoming Sessions Count
    sessions_count = query_dataframe(
        """
        SELECT COUNT(*) AS total 
        FROM sessions 
        WHERE student_id = %s 
          AND session_date >= %s
        """,
        (student_id, today_date)
    )

    # 4. Payments Summary
    payments_summary = query_dataframe(
        """
        SELECT COALESCE(SUM(amount), 0) AS total 
        FROM payments 
        WHERE student_id = %s
        """,
        (student_id,)
    )

    # 5. Single Next Session
    next_session = query_dataframe(
        """
        SELECT 
            s.session_date, 
            s.session_time, 
            s.topic, 
            st.zoom_link 
        FROM sessions s
        JOIN students st ON s.student_id = st.id
        WHERE s.student_id = %s AND s.session_date >= %s 
        ORDER BY s.session_date ASC, s.session_time ASC 
        LIMIT 1
        """,
        (student_id, today_date)
    )
    # 6. Homework Grades
    grades = query_dataframe(
        """
        SELECT
            title AS "Homework",
            due_date AS "Due Date",
            grade AS "Grade",
            teacher_feedback AS "Teacher Feedback",
            reviewed_at AS "Graded On"
        FROM homework
        WHERE student_id = %s
          AND grade IS NOT NULL
          AND TRIM(grade) <> ''
        ORDER BY due_date DESC
        """,
        (student_id,)
    )

    # 7. Session History
    sessions_history = query_dataframe(
        """
        SELECT
            s.session_date AS "Date",
            s.session_time AS "Time",
            s.duration AS "Duration",
            s.topic AS "Topic",
            s.status AS "Status",
            COALESCE(a.status, 'Pending') AS attendance_status,
            s.notes
        FROM sessions s
        LEFT JOIN attendance a ON a.student_id = s.student_id AND a.session_date = s.session_date
        WHERE s.student_id = %s
        ORDER BY s.session_date DESC, s.session_time DESC
        """,
        (student_id,)
    )

    # 8. Payments History
    payments_history = query_dataframe(
        """
        SELECT amount, payment_date, period 
        FROM payments 
        WHERE student_id = %s 
        ORDER BY payment_date DESC
        """,
        (student_id,)
    )

    return {
        "student_df": student_df,
        "homework_due": homework_due,
        "sessions_count": sessions_count,
        "payments_summary": payments_summary,
        "next_session": next_session,
        "grades": grades,
        "sessions_history": sessions_history,
        "payments_history": payments_history,
    }


def student_page():
    # Make sure missing columns are added automatically
    ensure_student_portal_schema()

    user = st.session_state.get("user", {})
    user_id = user.get("id")
    username = user.get("username")

    student_id = None

    # Dynamically resolve student_id from the database users table
    try:
        if user_id:
            res = query_dataframe("SELECT student_id FROM users WHERE id = %s", (user_id,))
            if not res.empty and res.iloc[0]["student_id"] is not None:
                student_id = int(res.iloc[0]["student_id"])
        elif username:
            res = query_dataframe("SELECT student_id FROM users WHERE username = %s", (username,))
            if not res.empty and res.iloc[0]["student_id"] is not None:
                student_id = int(res.iloc[0]["student_id"])
    except Exception:
        pass

    # Fallback to direct session dictionary value if query lookup is empty
    if not student_id and user.get("student_id"):
        try:
            student_id = int(user.get("student_id"))
        except (ValueError, TypeError):
            pass

    if not student_id:
        st.error("No linked student profile found for this user account. Please check with your administrator.")
        return

    st.sidebar.title("Student Portal")
    option = st.sidebar.radio("Menu", ["Dashboard", "Homework", "Performance & Account", "Schedule"])

    # Fetch cached bundle of student portal data
    data = get_student_portal_data(student_id, today_str())

    # ==========================
    # DASHBOARD
    # ==========================
    if option == "Dashboard":
        st.title("Student Dashboard")

        student = data["student_df"]

        if not student.empty:
            row = student.iloc[0]
            st.success(
                f"Welcome {row['first_name']} {row['last_name']} | "
                f"Grade: {row['grade']} | Subject: {row['subject']}"
            )

            hw_total = int(data["homework_due"].iloc[0]["total"]) if not data["homework_due"].empty else 0
            sess_total = int(data["sessions_count"].iloc[0]["total"]) if not data["sessions_count"].empty else 0
            pay_total = float(data["payments_summary"].iloc[0]["total"]) if not data["payments_summary"].empty else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric("📚 Homework Due", hw_total)
            c2.metric("📅 Total Upcoming", sess_total)
            c3.metric("💰 Payments Made", f"${pay_total:,.2f}")

            st.divider()
            st.subheader("Next Upcoming Session")
            
            next_session = data["next_session"]
            if not next_session.empty:
                s = next_session.iloc[0]
                st.info(f"**Date:** {s['session_date']} at {s['session_time']} | **Topic:** {s['topic']}")
                
                zoom_url = s.get("zoom_link")
                if zoom_url and str(zoom_url).strip() not in ["", "nan", "None"]:
                    st.markdown(f"🔗 [Join Zoom Meeting]({zoom_url})")
                else:
                    st.caption("No Zoom link assigned for this session yet.")
            else:
                st.write("No upcoming sessions scheduled.")
        else:
            st.warning(f"No student record found for Student ID: {student_id}")

    # ==========================
    # HOMEWORK
    # ==========================
    elif option == "Homework":
        from modules.homework import student_homework
        student_homework()

    # ============================================================
    # PERFORMANCE & ACCOUNT
    # ============================================================
    elif option == "Performance & Account":
        st.title("📊 Performance & Account")

        tab_grades, tab_sessions, tab_financial = st.tabs(
            [
                "📚 Homework Grades",
                "📅 Session History",
                "🔒 Financial Statement"
            ]
        )

        # ========================================================
        # HOMEWORK GRADES
        # ========================================================
        with tab_grades:
            st.subheader("Homework Grades")
            grades = data["grades"]

            if grades.empty:
                st.info("No graded homework available yet.")
            else:
                st.dataframe(grades, use_container_width=True, hide_index=True)

        # ========================================================
        # SESSION HISTORY
        # ========================================================
        with tab_sessions:
            st.subheader("Session History")
            sessions = data["sessions_history"][["Date", "Time", "Duration", "Topic", "Status"]]

            if sessions.empty:
                st.info("No session history available.")
            else:
                st.dataframe(sessions, use_container_width=True, hide_index=True)


        # ========================================================
        # FINANCIAL STATEMENT
        # ========================================================
        with tab_financial:
            st.subheader("🔒 Financial Statement")

            auth_key = f"parent_authenticated_{student_id}"

            if auth_key not in st.session_state:
                st.session_state[auth_key] = False

            if st.session_state[auth_key]:
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.success("🔓 Parent Access Authenticated")

                with col2:
                    if st.button("🔒 Lock", key=f"lock_financial_{student_id}"):
                        st.session_state[auth_key] = False
                        st.rerun()

                payments = data["payments_history"]

                if payments.empty:
                    st.info("No payment statements available.")
                else:
                    formatted_payments = payments.rename(columns={
                        "payment_date": "Payment Date",
                        "amount": "Amount Paid",
                        "period": "Period"
                    })
                    st.dataframe(formatted_payments, use_container_width=True, hide_index=True)

                    total_paid = formatted_payments["Amount Paid"].fillna(0).sum()
                    st.metric("Total Paid", f"${float(total_paid):,.2f}")

            else:
                st.warning("🔒 Financial information is confidential and requires Parent Authorization.")

                with st.container(border=True):
                    st.markdown("### 🔑 Parent Authentication Gateway")
                    st.write("Please enter the Parent Access PIN provided by the parent/guardian.")

                    pin_input = st.text_input(
                        "Parent Access PIN",
                        type="password",
                        key=f"parent_pin_input_{student_id}"
                    )

                    if st.button("Verify Identity & Unlock Financial Statement", type="primary", key=f"verify_parent_{student_id}"):
                        stored_pin_result = query_dataframe(
                            """
                            SELECT parent_pin
                            FROM students
                            WHERE id = %s
                            LIMIT 1
                            """,
                            (student_id,)
                        )

                        if stored_pin_result.empty:
                            st.error("No Parent Access PIN has been configured for this student.")
                        else:
                            stored_pin = stored_pin_result.iloc[0]["parent_pin"]

                            if stored_pin is not None and pin_input.strip() == str(stored_pin).strip():
                                st.session_state[auth_key] = True
                                st.rerun()
                            else:
                                st.error("Invalid Parent Access PIN.")

    # ==========================
    # SCHEDULE
    # ==========================
    elif option == "Schedule":
        st.title("My Sessions")
        sessions = data["sessions_history"]
        
        if sessions.empty:
            st.info("No sessions found.")
        else:
            for _, row in sessions.iterrows():
                with st.container():
                    att_status = row.get("attendance_status", "Pending")
                    if att_status == "Present":
                        badge = "✅ **Present**"
                    elif att_status == "Absent":
                        badge = "❌ **Absent**"
                    elif att_status == "Late":
                        badge = "⚠️ **Late**"
                    else:
                        badge = "⏳ **Pending / Not Marked**"

                    st.write(f"📅 **Date:** {row['Date']} at {row['Time']} | **Topic:** {row.get('Topic', 'N/A')} | **Attendance:** {badge}")
                    
                    if row.get("notes"):
                        st.caption(f"📝 Notes: {row['notes']}")
                    st.divider()

        # Render permanent classroom info in sidebar from cached student record
        student = data["student_df"]
        if not student.empty:
            z_link = student.iloc[0].get("zoom_link")
            m_id = student.iloc[0].get("meeting_id")
            if z_link or m_id:
                st.sidebar.divider()
                st.sidebar.subheader("Permanent Classroom Info")
                if z_link:
                    st.sidebar.markdown(f"🔗 [General Zoom Room]({z_link})")
                if m_id:
                    st.sidebar.text(f"Meeting ID: {m_id}")
