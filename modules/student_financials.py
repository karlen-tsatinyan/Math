import streamlit as st
import pandas as pd
from io import BytesIO

from database import query_dataframe


# ============================================================
# STUDENT FINANCIAL STATEMENTS
# ============================================================


def student_financials():

    st.title("💰 Financial Statements")


    # --------------------------------------------------------
    # Get student ID from logged-in user
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
            "Student account information is missing."
        )

        return


    try:

        student_id = int(
            student_id
        )

    except Exception:

        st.error(
            "Invalid student account."
        )

        return



    # --------------------------------------------------------
    # Get payment history
    # --------------------------------------------------------

    payments = query_dataframe(
        """
        SELECT
            id,
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


    # --------------------------------------------------------
    # No records
    # --------------------------------------------------------

    if payments.empty:

        st.info(
            "No financial statements are available yet."
        )

        return



    # --------------------------------------------------------
    # Clean data
    # --------------------------------------------------------

    payments["amount"] = pd.to_numeric(
        payments["amount"],
        errors="coerce"
    ).fillna(0)



    payments["payment_date"] = (
        payments["payment_date"]
        .astype(str)
    )



    payments["period"] = (
        payments["period"]
        .fillna("")
        .astype(str)
    )



    payments["status"] = (
        payments["status"]
        .fillna("")
        .astype(str)
    )



    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    total_paid = payments["amount"].sum()


    payment_count = len(
        payments
    )


    col1, col2 = st.columns(2)


    with col1:

        st.metric(
            "💵 Total Paid",
            f"${total_paid:,.2f}"
        )


    with col2:

        st.metric(
            "🧾 Payment Records",
            payment_count
        )



    st.divider()



    # --------------------------------------------------------
    # Statement Table
    # --------------------------------------------------------

    st.subheader(
        "📄 Statement of Account"
    )


    statement = payments[
        [
            "payment_date",
            "period",
            "amount",
            "status"
        ]
    ].copy()



    statement = statement.rename(
        columns={
            "payment_date": "Payment Date",
            "period": "Period",
            "amount": "Amount",
            "status": "Status"
        }
    )



    statement["Amount"] = statement[
        "Amount"
    ].apply(
        lambda x: f"${x:,.2f}"
    )



    st.dataframe(
        statement,
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



    # -------------------------
    # CSV
    # -------------------------

    csv_file = payments.to_csv(
        index=False
    )


    st.download_button(
        label="📥 Download CSV",
        data=csv_file,
        file_name="financial_statement.csv",
        mime="text/csv"
    )



    # -------------------------
    # Excel
    # -------------------------

    try:

        excel_buffer = BytesIO()


        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            payments.to_excel(
                writer,
                index=False,
                sheet_name="Payments"
            )


        excel_buffer.seek(0)


        st.download_button(
            label="📊 Download Excel",
            data=excel_buffer,
            file_name="financial_statement.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )


    except Exception as e:

        st.warning(
            f"Excel export unavailable: {e}"
        )



    st.divider()



    # --------------------------------------------------------
    # Privacy
    # --------------------------------------------------------

    st.caption(
        "🔒 This financial information is private to your account."
    )
