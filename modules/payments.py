import streamlit as st
from datetime import date
from database import execute, query_dataframe


def ensure_payments_schema():
    """Safely ensure essential columns exist in the payments table."""
    columns_to_add = [
        ("payments", "amount", "NUMERIC DEFAULT 0.00"),
        ("payments", "payment_date", "DATE DEFAULT CURRENT_DATE"),
        ("payments", "period", "TEXT"),
        ("payments", "status", "TEXT DEFAULT 'Completed'"),
    ]

    for table_name, col_name, col_type in columns_to_add:
        try:
            execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                """
            )
        except Exception:
            pass


def payment_management():

    # Automatically patch any missing columns
    ensure_payments_schema()

    st.title("💰 Payment Management")

    # ==========================================================
    # TABS
    # ==========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "💳 Payment History",
            "➕ Record Payment",
            "✏️ Edit / Manage Payments"
        ]
    )

    # ==========================================================
    # TAB 1 — PAYMENT HISTORY
    # ==========================================================

    with tab1:

        st.subheader("Payment Records")

        try:

            payments = query_dataframe(
                """
                SELECT
                    p.id,
                    s.first_name || ' ' || s.last_name AS student_name,
                    COALESCE(p.amount, 0.00) AS amount,
                    COALESCE(p.payment_date, CURRENT_DATE) AS payment_date,
                    COALESCE(p.period, '') AS period,
                    COALESCE(p.status, 'Completed') AS status

                FROM payments p

                JOIN students s
                    ON p.student_id = s.id

                ORDER BY p.payment_date DESC
                """
            )

            if not payments.empty:

                st.dataframe(
                    payments,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "No payment records found."
                )

        except Exception as e:

            st.error(
                f"Error loading payment history: {e}"
            )

    # ==========================================================
    # TAB 2 — RECORD PAYMENT
    # ==========================================================

    with tab2:

        st.subheader("Record New Payment")

        # ------------------------------------------------------
        # GET ACTIVE STUDENTS
        # ------------------------------------------------------

        students = query_dataframe(
            """
            SELECT
                id,
                first_name || ' ' || last_name AS name

            FROM students

            WHERE COALESCE(archived, 0) = 0

            ORDER BY last_name, first_name
            """
        )

        if students.empty:

            st.warning(
                "No active students available."
            )

        else:

            with st.form("payment_form"):

                # --------------------------------------------------
                # STUDENT
                # --------------------------------------------------

                student_name = st.selectbox(
                    "Student",
                    students["name"].tolist(),
                    key="payment_student_select"
                )

                student_id_input = int(
                    students[
                        students["name"] == student_name
                    ]["id"].iloc[0]
                )

                # --------------------------------------------------
                # AMOUNT
                # --------------------------------------------------

                amount_input = st.number_input(
                    "Amount ($)",
                    min_value=0.0,
                    format="%.2f",
                    key="payment_amount"
                )

                # --------------------------------------------------
                # PAYMENT DATE
                # --------------------------------------------------

                payment_date_input = st.date_input(
                    "Payment Date",
                    value=date.today(),
                    key="payment_date_input"
                )

                # --------------------------------------------------
                # PERIOD
                # --------------------------------------------------

                period_input = st.text_input(
                    "Period (e.g., June 2026)",
                    key="payment_period"
                )

                # --------------------------------------------------
                # SAVE
                # --------------------------------------------------

                submitted = st.form_submit_button(
                    "💾 Save Payment"
                )

                if submitted:

                    if amount_input <= 0:

                        st.error(
                            "Please enter a payment amount greater than $0."
                        )

                    elif not period_input.strip():

                        st.error(
                            "Please enter the period this payment covers."
                        )

                    else:

                        try:

                            execute(
                                """
                                INSERT INTO payments
                                (
                                    student_id,
                                    amount,
                                    payment_date,
                                    period,
                                    status
                                )
                                VALUES
                                (
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    'Completed'
                                )
                                """,
                                (
                                    student_id_input,
                                    amount_input,
                                    str(payment_date_input),
                                    period_input.strip()
                                )
                            )

                            # Clear cached database results
                            st.cache_data.clear()

                            st.success(
                                "✅ Payment successfully recorded!"
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Error saving payment: {e}"
                            )

    # ==========================================================
    # TAB 3 — EDIT / MANAGE PAYMENTS
    # ==========================================================

    with tab3:

        st.subheader(
            "Edit or Remove Payment Entries"
        )

        try:

            payments_list = query_dataframe(
                """
                SELECT
                    p.id,
                    p.student_id,
                    s.first_name || ' ' || s.last_name
                        AS student_name,
                    p.amount,
                    p.payment_date,
                    p.period,
                    p.status

                FROM payments p

                JOIN students s
                    ON p.student_id = s.id

                ORDER BY p.payment_date DESC, p.id DESC
                """
            )

            if not payments_list.empty:

                # --------------------------------------------------
                # PAYMENT SELECTOR
                # --------------------------------------------------

                payment_options = {}

                for _, row in payments_list.iterrows():

                    payment_date_display = (
                        str(row["payment_date"])
                        if row["payment_date"] is not None
                        else ""
                    )

                    period_display = (
                        str(row["period"])
                        if row["period"] is not None
                        else ""
                    )

                    amount_display = (
                        f"{float(row['amount']):.2f}"
                        if row["amount"] is not None
                        else "0.00"
                    )

                    label = (
                        f"{row['student_name']} — "
                        f"${amount_display} — "
                        f"{payment_date_display} — "
                        f"{period_display}"
                    )

                    payment_options[label] = row["id"]

                selected_label = st.selectbox(
                    "Select Payment to Edit",
                    list(payment_options.keys()),
                    key="edit_payment_select"
                )

                if selected_label:

                    selected_id = payment_options[
                        selected_label
                    ]

                    selected_row = payments_list[
                        payments_list["id"] == selected_id
                    ].iloc[0]

                    # --------------------------------------------------
                    # EDIT FORM
                    # --------------------------------------------------

                    with st.form("edit_payment_form"):

                        new_amount = st.number_input(
                            "Update Amount ($)",
                            min_value=0.0,
                            value=float(
                                selected_row["amount"] or 0
                            ),
                            format="%.2f",
                            key=f"edit_amount_{selected_id}"
                        )

                        # --------------------------------------------------
                        # EDIT PAYMENT DATE
                        # --------------------------------------------------

                        existing_date = selected_row[
                            "payment_date"
                        ]

                        if pd_is_valid_date(existing_date):

                            if hasattr(
                                existing_date,
                                "date"
                            ):
                                existing_date = (
                                    existing_date.date()
                                )

                            elif not isinstance(
                                existing_date,
                                date
                            ):
                                existing_date = date.today()

                        else:

                            existing_date = date.today()

                        new_payment_date = st.date_input(
                            "Update Payment Date",
                            value=existing_date,
                            key=f"edit_payment_date_{selected_id}"
                        )

                        new_period = st.text_input(
                            "Update Period",
                            value=str(
                                selected_row["period"] or ""
                            ),
                            key=f"edit_period_{selected_id}"
                        )

                        col1, col2 = st.columns(2)

                        update_sub = col1.form_submit_button(
                            "🔄 Update Payment"
                        )

                        delete_sub = col2.form_submit_button(
                            "🗑️ Delete Payment"
                        )

                        # --------------------------------------------------
                        # UPDATE PAYMENT
                        # --------------------------------------------------

                        if update_sub:

                            if new_amount <= 0:

                                st.error(
                                    "Payment amount must be greater than $0."
                                )

                            elif not new_period.strip():

                                st.error(
                                    "Please enter the payment period."
                                )

                            else:

                                execute(
                                    """
                                    UPDATE payments

                                    SET
                                        amount = %s,
                                        payment_date = %s,
                                        period = %s,
                                        status = 'Completed'

                                    WHERE id = %s
                                    """,
                                    (
                                        new_amount,
                                        str(new_payment_date),
                                        new_period.strip(),
                                        selected_id
                                    )
                                )

                                st.cache_data.clear()

                                st.success(
                                    "✅ Payment updated successfully!"
                                )

                                st.rerun()

                        # --------------------------------------------------
                        # DELETE PAYMENT
                        # --------------------------------------------------

                        if delete_sub:

                            execute(
                                """
                                DELETE FROM payments
                                WHERE id = %s
                                """,
                                (selected_id,)
                            )

                            st.cache_data.clear()

                            st.success(
                                "✅ Payment deleted successfully!"
                            )

                            st.rerun()

            else:

                st.info(
                    "No payments available to edit."
                )

        except Exception as e:

            st.error(
                f"Error loading management interface: {e}"
            )


# ==========================================================
# HELPER FOR DATE VALIDATION
# ==========================================================

def pd_is_valid_date(value):
    """
    Safely determine whether a database date value
    can be converted into a Python date.
    """

    if value is None:
        return False

    try:

        if hasattr(value, "date"):
            return True

        if isinstance(value, date):
            return True

        # Handle string dates such as 2026-08-14
        if isinstance(value, str):

            date.fromisoformat(
                value[:10]
            )

            return True

        return False

    except Exception:

        return False
