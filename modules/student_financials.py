import streamlit as st
import pandas as pd
from io import BytesIO

from database import query_dataframe


# ============================================================
# GET STUDENT PARENT PIN
# ============================================================

def get_parent_pin(student_id):

    result = query_dataframe(
        """
        SELECT
            parent_pin
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (
            student_id,
        )
    )

    if result.empty:
        return None

    return result.iloc[0]["parent_pin"]



# ============================================================
# GET PAYMENTS
# ============================================================

def get_payment_history(student_id):

    return query_dataframe(
        """
        SELECT
            payment_date,
            amount,
            period,
            status
        FROM payments
        WHERE student_id = %s
        ORDER BY payment_date DESC
        """,
        (
            student_id,
        )
    )



# ============================================================
# FINANCIAL STATEMENTS PAGE
# ============================================================

def student_financials():


    st.title(
        "💰 Financial Statements"
    )


    # --------------------------------------------------------
    # Student ID
    # --------------------------------------------------------

    user = st.session_state.get(
        "user",
        {}
    )


    student_id = user.get(
        "student_id"
    )


    if not student_id:

        st.error(
            "Student account not found."
        )

        return


    student_id = int(student_id)



    # --------------------------------------------------------
    # Parent PIN Authentication
    # --------------------------------------------------------

    auth_key = (
        f"financial_unlocked_{student_id}"
    )


    if not st.session_state.get(
        auth_key,
        False
    ):


        st.info(
            "🔒 Financial statements are protected. "
            "Please enter the Parent PIN to continue."
        )


        pin_input = st.text_input(
            "Parent PIN",
            type="password",
            key=f"parent_pin_{student_id}"
        )


        if st.button(
            "🔓 Unlock Financial Statements",
            key=f"unlock_financial_{student_id}"
        ):


            correct_pin = get_parent_pin(
                student_id
            )


            if (
                correct_pin
                and str(pin_input).strip()
                ==
                str(correct_pin).strip()
            ):

                st.session_state[
                    auth_key
                ] = True


                st.success(
                    "✅ Financial statements unlocked."
                )


                st.rerun()


            else:

                st.error(
                    "❌ Incorrect Parent PIN."
                )


        return



    # --------------------------------------------------------
    # Locked State Button
    # --------------------------------------------------------

    if st.button(
        "🔒 Lock Financial Statements",
        key=f"lock_financial_{student_id}"
    ):

        st.session_state[
            auth_key
        ] = False

        st.rerun()



    st.divider()



    # --------------------------------------------------------
    # Load Payments
    # --------------------------------------------------------

    payments = get_payment_history(
        student_id
    )


    if payments.empty:

        st.info(
            "No payment records found."
        )

        return



    payments["amount"] = pd.to_numeric(
        payments["amount"],
        errors="coerce"
    ).fillna(0)



    total_paid = payments[
        "amount"
    ].sum()



    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    c1, c2 = st.columns(2)


    with c1:

        st.metric(
            "💵 Total Paid",
            f"${total_paid:,.2f}"
        )


    with c2:

        st.metric(
            "🧾 Payments",
            len(payments)
        )



    st.divider()



    # --------------------------------------------------------
    # Statement
    # --------------------------------------------------------

    st.subheader(
        "📄 Statement of Account"
    )


    display = payments.copy()


    display = display.rename(
        columns={
            "payment_date":
                "Payment Date",

            "amount":
                "Amount",

            "period":
                "Period",

            "status":
                "Status"
        }
    )


    display["Amount"] = display[
        "Amount"
    ].apply(
        lambda x: f"${x:,.2f}"
    )


    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )



    st.divider()



    # --------------------------------------------------------
    # Downloads
    # --------------------------------------------------------

    st.subheader(
        "⬇️ Download Statement"
    )


    csv = payments.to_csv(
        index=False
    )


    st.download_button(
        "📥 Download CSV",
        csv,
        file_name="financial_statement.csv",
        mime="text/csv"
    )



    try:

        buffer = BytesIO()


        with pd.ExcelWriter(
            buffer,
            engine="openpyxl"
        ) as writer:

            payments.to_excel(
                writer,
                index=False,
                sheet_name="Payments"
            )


        buffer.seek(0)


        st.download_button(
            "📊 Download Excel",
            buffer,
            file_name="financial_statement.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )


    except Exception:

        pass



    st.caption(
        "🔒 Financial information is protected by Parent PIN authentication."
    )
