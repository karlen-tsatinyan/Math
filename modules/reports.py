import streamlit as st
import pandas as pd

from datetime import date

from database import query_dataframe



def reports_management():


    st.header(
        "Financial Report Generator"
    )


    col1, col2 = st.columns(2)


    with col1:

        start_date = st.date_input(
            "Start Date",
            value=date.today()
        )


    with col2:

        end_date = st.date_input(
            "End Date",
            value=date.today()
        )



    payments = query_dataframe(

        """

        SELECT

        s.first_name || ' ' || s.last_name AS Student,

        p.amount AS Amount,

        p.payment_date AS Date,

        p.period AS Period


        FROM payments p


        JOIN students s

        ON p.student_id=s.id


        WHERE

        p.payment_date BETWEEN ? AND ?


        ORDER BY p.payment_date DESC


        """,

        (

            str(start_date),

            str(end_date)

        )

    )


    sessions = query_dataframe(

        """

        SELECT

        COUNT(*) AS total_sessions

        FROM sessions


        WHERE

        session_date BETWEEN ? AND ?


        """,

        (

            str(start_date),

            str(end_date)

        )

    )



    students = query_dataframe(

        """

        SELECT

        COUNT(DISTINCT student_id)

        AS active_students


        FROM payments


        WHERE

        payment_date BETWEEN ? AND ?


        """,

        (

            str(start_date),

            str(end_date)

        )

    )



    # ==========================
    # KPI CARDS
    # ==========================


    revenue = payments["Amount"].sum()


    total_sessions = int(
        sessions.iloc[0]["total_sessions"]
    )


    active_students = int(
        students.iloc[0]["active_students"]
    )


    c1,c2,c3 = st.columns(3)


    c1.metric(
        "Revenue",
        f"${revenue:,.2f}"
    )


    c2.metric(
        "Sessions",
        total_sessions
    )


    c3.metric(
        "Active Students",
        active_students
    )



    st.divider()


    st.subheader(
        "Payment Details"
    )


    st.dataframe(

        payments,

        use_container_width=True

    )



    # ==========================
    # STUDENT SUMMARY
    # ==========================


    st.subheader(

        "Student Payment Summary"

    )


    summary=query_dataframe(

        """

        SELECT


        s.first_name || ' ' || s.last_name AS Student,


        SUM(p.amount) AS Total_Paid,


        MAX(p.payment_date) AS Last_Payment,


        MAX(p.period) AS Last_Period


        FROM payments p


        JOIN students s


        ON p.student_id=s.id


        GROUP BY s.id


        ORDER BY Total_Paid DESC


        """

    )


    st.dataframe(

        summary,

        use_container_width=True

    )



    # ==========================
    # EXPORT EXCEL
    # ==========================


    if len(summary)>0:


        file = "financial_report.xlsx"


        with pd.ExcelWriter(file) as writer:


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



        with open(file,"rb") as f:


            st.download_button(

                label="Download Excel Report",

                data=f,

                file_name=file,

                mime=
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            )