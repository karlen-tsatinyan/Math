import streamlit as st
import pandas as pd
from datetime import date

from database import (
    execute,
    query_dataframe
)



def payment_management():


    st.header(
        "Payment Management"
    )


    students = query_dataframe(
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
            "No students found. Add students first."
        )

        return



    tab1, tab2 = st.tabs(
        [
            "Add Payment",
            "Payment History"
        ]
    )


    # -----------------------------
    # ADD PAYMENT
    # -----------------------------

    with tab1:


        student = st.selectbox(

            "Select Student",

            students["name"].tolist()

        )


        student_id = int(
            students[
                students["name"]==student
            ]["id"].iloc[0]
        )


        amount = st.number_input(

            "Payment Amount",

            min_value=0.0,

            step=25.0

        )


        payment_date = st.date_input(

            "Payment Date",

            value=date.today()

        )


        period = st.text_input(

            "Payment Period",

            placeholder="Example: January Week 1"

        )


        notes = st.text_area(
            "Notes"
        )


        if st.button(
            "Save Payment"
        ):


            execute(

                """
                INSERT INTO payments
                (
                    student_id,
                    amount,
                    payment_date,
                    period,
                    notes
                )

                VALUES
                (?,?,?,?,?)

                """,

                (

                    student_id,

                    amount,

                    payment_date,

                    period,

                    notes

                )

            )


            st.success(
                "Payment saved."
            )



    # -----------------------------
    # HISTORY
    # -----------------------------

    with tab2:


        payments = query_dataframe(

            """
            SELECT

            s.first_name || ' ' || s.last_name AS Student,

            p.amount AS Amount,

            p.payment_date AS Date,

            p.period AS Period,

            p.notes AS Notes


            FROM payments p


            JOIN students s

            ON p.student_id=s.id


            ORDER BY p.payment_date DESC

            """

        )


        st.dataframe(

            payments,

            use_container_width=True

        )



        if len(payments)>0:


            st.metric(

                "Total Revenue",

                f"${payments['Amount'].sum():,.2f}"

            )