import io
from datetime import date
import pandas as pd
import streamlit as st

from database import query_dataframe


def reports_management():
    st.header("📊 Financial Report Generator")

    # ==========================
    # DATE RANGE CONTROLS
    # ==========================
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date", value=date.today().replace(day=1))

    with col2:
        end_date = st.date_input("End Date", value=date.today())

    # Date range validation
    if start_date > end_date:
        st.error("Error: 'Start Date' cannot be after 'End Date'. Please adjust your selection.")
        return

    # Convert dates to ISO strings for SQL compatibility
    str_start = str(start_date)
    str_end = str(end_date)

    # ==========================
    # DATA QUERIES
    # ==========================
    payments = query_dataframe(
        """
        SELECT
            s.first_name || ' ' || s.last_name AS Student,
            p.amount AS Amount,
            p.payment_date AS Date,
            p.period AS Period
        FROM payments p
        JOIN students s ON p.student_id = s.id
        WHERE p.payment_date BETWEEN ? AND ?
        ORDER BY p.payment_date DESC
        """,
        (str_start, str_end)
    )

    sessions = query_dataframe(
        """
        SELECT COUNT(*) AS total_sessions
        FROM sessions
        WHERE session_date BETWEEN ? AND ?
        """,
        (str_start, str_end)
    )

    students = query_dataframe(
        """
        SELECT COUNT(DISTINCT student_id) AS active_students
        FROM payments
        WHERE payment_date BETWEEN ? AND ?
        """,
        (str_start, str_end)
    )

    summary = query_dataframe(
        """
        SELECT
            s.first_name || ' ' || s.last_name AS Student,
            SUM(p.amount) AS Total_Paid,
            MAX(p.payment_date) AS Last_Payment,
            MAX(p.period) AS Last_Period
        FROM payments p
        JOIN students s ON p.student_id = s.id
        WHERE p.payment_date BETWEEN ? AND ?
        GROUP BY s.id
        ORDER BY Total_Paid DESC
        """,
        (str_start, str_end)
    )

    # ==========================
    # KPI CARDS
    # ==========================
    revenue = payments["Amount"].sum() if not payments.empty and "Amount" in payments.columns else 0.0
    total_sessions = int(sessions.iloc[0]["total_sessions"]) if not sessions.empty else 0
    active_students = int(students.iloc[0]["active_students"]) if not students.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", f"${revenue:,.2f}")
    c2.metric("Total Sessions", total_sessions)
    c3.metric("Active Paying Students", active_students)

    st.divider()

    # ==========================
    # DATA TABLES
    # ==========================
    st.subheader("💳 Payment Details")
    if not payments.empty:
        st.dataframe(
            payments,
            use_container_width=True,
            column_config={
                "Amount": st.column_config.NumberColumn("Amount", format="$%.2f")
            }
        )
    else:
        st.info("No payment records found for the selected date range.")

    st.subheader("👥 Student Payment Summary")
    if not summary.empty:
        st.dataframe(
            summary,
            use_container_width=True,
            column_config={
                "Total_Paid": st.column_config.NumberColumn("Total Paid", format="$%.2f")
            }
        )
    else:
        st.info("No summary data available for this range.")

    # ==========================
    # EXPORT IN-MEMORY EXCEL
    # ==========================
    st.divider()
    if not summary.empty or not payments.empty:
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            payments.to_excel(writer, sheet_name="Payments", index=False)
            summary.to_excel(writer, sheet_name="Student Summary", index=False)

        st.download_button(
            label="📥 Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"financial_report_{str_start}_to_{str_end}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
