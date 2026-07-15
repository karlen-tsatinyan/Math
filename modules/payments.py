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

    # ---------------------------------
    # Remember selected student
    # ---------------------------------

    selected_student_id = st.session_state.get("selected_student")

    student_names = students["name"].tolist()

    default_index = 0

    if selected_student_id is not None:

        match = students[
            students["id"] == selected_student_id
        ]

        if len(match) > 0:

            default_index = match.index[0]


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Payment",
            "Payment History",
            "Edit Payment"
        ]
    )


    # -----------------------------
    # ADD PAYMENT
    # -----------------------------

    with tab1:

        student = st.selectbox(

            "Select Student",

            student_names,

            index=default_index

        )


        student_id = int(
            students[
                students["name"]==student
            ]["id"].iloc[0]
        )
        
        st.session_state.selected_student = student_id

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

    # -----------------------------
    # EDIT PAYMENT
    # -----------------------------

    with tab3:

        payments = query_dataframe(
            """
            SELECT

                p.id,

                s.first_name || ' ' || s.last_name AS Student,

                p.amount,

                p.payment_date,

                p.period,

                p.notes

            FROM payments p

            JOIN students s
                ON p.student_id = s.id

            ORDER BY p.payment_date DESC
            """
        )

        if len(payments) == 0:

            st.info("No payments to edit.")

        else:

            payment_id = st.selectbox(

                "Select Payment",

                payments["id"],

                format_func=lambda x:
                    f"#{x} - " +
                    payments.loc[
                        payments["id"] == x,
                        "Student"
                    ].iloc[0]

            )

            payment = payments[
                payments["id"] == payment_id
            ].iloc[0]

            amount = st.number_input(
                "Payment Amount",
                min_value=0.0,
                value=float(payment["amount"]),
                step=25.0,
                key="edit_amount"
            )

            payment_date = st.date_input(
                "Payment Date",
                value=pd.to_datetime(payment["payment_date"]).date(),
                key="edit_date"
            )

            period = st.text_input(
                "Payment Period",
                value=payment["period"] if payment["period"] else "",
                key="edit_period"
            )

            notes = st.text_area(
                "Notes",
                value=payment["notes"] if payment["notes"] else "",
                key="edit_notes"
            )


            if st.button(
                "💾 Update Payment"
            ):

                execute(

                    """
                    UPDATE payments

                    SET

                        amount=?,

                        payment_date=?,

                        period=?,

                        notes=?

                    WHERE id=?

                    """,

                    (

                        amount,

                        str(payment_date),

                        period,

                        notes,

                        int(payment_id)

                    )

                )

                st.success("Payment updated successfully.")

                st.rerun()