import io
from datetime import date

import pandas as pd
import streamlit as st

from database import query_dataframe

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

def create_financial_report_pdf(
    payments,
    summary,
    start_date,
    end_date,
    student_name
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    elements = []

    # ========================================================
    # TITLE
    # ========================================================

    elements.append(
        Paragraph(
            "Financial Report",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            f"Report Period: {start_date} to {end_date}",
            styles["Normal"]
        )
    )

    if student_name != "All Students":

        elements.append(
            Paragraph(
                f"Student: {student_name}",
                styles["Normal"]
            )
        )

    elements.append(
        Spacer(1, 15)
    )

    # ========================================================
    # PAYMENT DETAILS
    # ========================================================

    elements.append(
        Paragraph(
            "Payment Details",
            styles["Heading2"]
        )
    )

    if not payments.empty:

        pdf_payments = payments.copy()

        pdf_payments = pdf_payments.fillna("")

        data = [
            list(pdf_payments.columns)
        ]

        for _, row in pdf_payments.iterrows():

            data.append(
                [
                    str(value)
                    for value in row.tolist()
                ]
            )

        table = Table(
            data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.grey
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    )
                ]
            )
        )

        elements.append(table)

    else:

        elements.append(
            Paragraph(
                "No payment records found.",
                styles["Normal"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # ========================================================
    # STUDENT PAYMENT SUMMARY
    # ========================================================

    elements.append(
        Paragraph(
            "Student Payment Summary",
            styles["Heading2"]
        )
    )

    if not summary.empty:

        pdf_summary = summary.copy()

        pdf_summary = pdf_summary.fillna("")

        data = [
            list(pdf_summary.columns)
        ]

        for _, row in pdf_summary.iterrows():

            data.append(
                [
                    str(value)
                    for value in row.tolist()
                ]
            )

        table = Table(
            data,
            repeatRows=1
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.grey
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    )
                ]
            )
        )

        elements.append(table)

    else:

        elements.append(
            Paragraph(
                "No summary data available.",
                styles["Normal"]
            )
        )

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(elements)

    buffer.seek(0)

    return buffer.getvalue()

def reports_management():

    st.header("📊 Financial Report Generator")

    # ==========================
    # FILTERS
    # ==========================

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(day=1)
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today()
        )

    if start_date > end_date:
        st.error(
            "Start Date cannot be after End Date."
        )
        return


    str_start = str(start_date)
    str_end = str(end_date)


    # ==========================
    # STUDENT FILTER
    # ==========================

    students_df = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS student_name
        FROM students
        ORDER BY first_name, last_name
        """
    )


    student_options = {
        "All Students": None
    }


    if not students_df.empty:

        for _, row in students_df.iterrows():

            student_options[
                row["student_name"]
            ] = row["id"]


    with col3:

        selected_student_name = st.selectbox(
            "Filter by Student",
            list(student_options.keys())
        )


    selected_student_id = student_options[selected_student_name]


    # ==========================
    # PAYMENT SUMMARY
    # ==========================

    summary = query_dataframe(
        """
        SELECT
            s.first_name || ' ' || s.last_name AS Student,
            SUM(p.amount) AS Total_Paid,
            MAX(p.payment_date) AS Last_Payment,
            MAX(p.period) AS Last_Period

        FROM payments p

        JOIN students s
            ON p.student_id = s.id

        WHERE p.payment_date BETWEEN %s AND %s

        GROUP BY s.id,
                 s.first_name,
                 s.last_name

        ORDER BY Total_Paid DESC
        """,
        (
            str_start,
            str_end
        )
    )


    # ==========================
    # FILTERED DATA
    # ==========================

    if selected_student_id:


        payments = query_dataframe(
            """
            SELECT

                s.first_name || ' ' || s.last_name AS Student,
                p.amount AS "Amount",
                p.payment_date AS "Date",
                p.period AS "Period"

            FROM payments p

            JOIN students s
                ON p.student_id = s.id

            WHERE p.payment_date BETWEEN %s AND %s
            AND p.student_id = %s

            ORDER BY p.payment_date DESC

            """,
            (
                str_start,
                str_end,
                selected_student_id
            )
        )


        sessions = query_dataframe(
            """
            SELECT
                COUNT(*) AS total_sessions

            FROM sessions

            WHERE session_date BETWEEN %s AND %s
            AND student_id = %s

            """,
            (
                str_start,
                str_end,
                selected_student_id
            )
        )


        students_count = query_dataframe(
            """
            SELECT
                COUNT(DISTINCT student_id) AS active_students

            FROM payments

            WHERE payment_date BETWEEN %s AND %s
            AND student_id = %s

            """,
            (
                str_start,
                str_end,
                selected_student_id
            )
        )


    else:


        payments = query_dataframe(
            """
            SELECT

                s.first_name || ' ' || s.last_name AS Student,
                p.amount AS "Amount",
                p.payment_date AS "Date",
                p.period AS "Period"

            FROM payments p

            JOIN students s
                ON p.student_id = s.id

            WHERE p.payment_date BETWEEN %s AND %s

            ORDER BY p.payment_date DESC

            """,
            (
                str_start,
                str_end
            )
        )


        sessions = query_dataframe(
            """
            SELECT
                COUNT(*) AS total_sessions

            FROM sessions

            WHERE session_date BETWEEN %s AND %s

            """,
            (
                str_start,
                str_end
            )
        )


        students_count = query_dataframe(
            """
            SELECT
                COUNT(DISTINCT student_id) AS active_students

            FROM payments

            WHERE payment_date BETWEEN %s AND %s

            """,
            (
                str_start,
                str_end
            )
        )


    # ==========================
    # KPI CARDS
    # ==========================

    revenue = 0.0

    if not payments.empty:
    
        if "Amount" in payments.columns:
            revenue = payments["Amount"].sum()
    
        elif "amount" in payments.columns:
            revenue = payments["amount"].sum()


    total_sessions = 0

    if not sessions.empty:
        total_sessions = int(
            sessions.iloc[0]["total_sessions"]
        )


    active_students = 0

    if not students_count.empty:
        active_students = int(
            students_count.iloc[0]["active_students"]
        )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Total Revenue",
        f"${revenue:,.2f}"
    )

    c2.metric(
        "Total Sessions",
        total_sessions
    )

    c3.metric(
        "Active Paying Students",
        active_students
    )


    st.divider()


    # ==========================
    # TABLES
    # ==========================

    st.subheader(
        f"💳 Payment Details "
        f"{selected_student_name if selected_student_id else ''}"
    )


    if not payments.empty:

        st.dataframe(
            payments,
            use_container_width=True
        )

    else:

        st.info(
            "No payment records found."
        )



    st.subheader(
        "👥 Student Payment Summary"
    )


    if not summary.empty:

        st.dataframe(
            summary,
            use_container_width=True
        )

    else:

        st.info(
            "No summary data available."
        )


    # ==========================
    # EXPORT
    # ==========================
    
    if not summary.empty or not payments.empty:
    
        st.subheader(
            "⬇️ Download Reports"
        )
    
        col1, col2 = st.columns(2)
    
        # ========================================================
        # EXCEL
        # ========================================================
    
        with col1:
    
            buffer = io.BytesIO()
    
            with pd.ExcelWriter(
                buffer,
                engine="openpyxl"
            ) as writer:
    
                payments.to_excel(
                    writer,
                    sheet_name="Payments",
                    index=False
                )
    
                summary.to_excel(
                    writer,
                    sheet_name="Student Summary",
                    index=False
                )
    
            st.download_button(
    
                label="📊 Download Excel",
    
                data=buffer.getvalue(),
    
                file_name=
                f"financial_report_{str_start}_to_{str_end}.xlsx",
    
                mime=
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    
                use_container_width=True,
    
                key="download_financial_excel"
    
            )
    
        # ========================================================
        # PDF
        # ========================================================
    
        with col2:
    
            pdf_data = create_financial_report_pdf(
    
                payments,
    
                summary,
    
                str_start,
    
                str_end,
    
                selected_student_name
    
            )
    
            st.download_button(
    
                label="📄 Download PDF",
    
                data=pdf_data,
    
                file_name=
                f"financial_report_{str_start}_to_{str_end}.pdf",
    
                mime="application/pdf",
    
                use_container_width=True,
    
                key="download_financial_pdf"
    
            )
