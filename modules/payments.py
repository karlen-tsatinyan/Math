import streamlit as st
from datetime import date
from database import execute, query_dataframe


def payment_management():

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
                    p.payment_date,
                    COALESCE(p.period, '') AS period,
                    COALESCE(p.status, 'Completed') AS status
                FROM payments p
                JOIN students s
                    ON p.student_id = s.id
                ORDER BY p.payment_date DESC, p.id DESC
                """
            )

            if not payments.empty:

                display_payments = payments.rename(
                    columns={
                        "id": "Payment ID",
                        "student_name": "Student",
                        "amount": "Amount",
                        "payment_date": "Payment Date",
                        "period": "Period",
                        "status": "Status"
                    }
                )

                st.dataframe(
                    display_payments,
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
                    step=0.01,
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
                    "Period Paid For",
                    placeholder="e.g., August 2026",
                    key="payment_period"
                )

                # --------------------------------------------------
                # SUBMIT
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
                            "Please enter the period the payment is for."
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
                                    payment_date_input,
                                    period_input.strip()
                                )
                            )

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
                    s.first_name || ' ' || s.last_name AS student_name,
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

            if payments_list.empty:

                st.info(
                    "No payments available to edit."
                )

            else:

                # --------------------------------------------------
                # PAYMENT SELECTOR
                # --------------------------------------------------

                payment_options = {}

                for _, row in payments_list.iterrows():

                    amount = (
                        float(row["amount"])
                        if row["amount"] is not None
                        else 0.0
                    )

                    payment_date_display = (
                        str(row["payment_date"])
                        if row["payment_date"] is not None
                        else "No date"
                    )

                    period_display = (
                        str(row["period"])
                        if row["period"] is not None
                        else ""
                    )

                    label = (
                        f"{row['student_name']} — "
                        f"${amount:,.2f} — "
                        f"{payment_date_display} — "
                        f"{period_display}"
                    )

                    payment_options[label] = int(
                        row["id"]
                    )

                selected_label = st.selectbox(
                    "Select Payment to Edit",
                    list(payment_options.keys()),
                    key="payment_edit_selector"
                )

                selected_id = payment_options[
                    selected_label
                ]

                selected_rows = payments_list[
                    payments_list["id"] == selected_id
                ]

                if not selected_rows.empty:

                    selected_row = (
                        selected_rows.iloc[0]
                    )

                    # --------------------------------------------------
                    # EDIT FORM
                    # --------------------------------------------------

                    with st.form(
                        f"edit_payment_form_{selected_id}"
                    ):

                        st.write(
                            f"**Student:** "
                            f"{selected_row['student_name']}"
                        )

                        # --------------------------------------------------
                        # AMOUNT
                        # --------------------------------------------------

                        current_amount = (
                            float(selected_row["amount"])
                            if selected_row["amount"] is not None
                            else 0.0
                        )

                        new_amount = st.number_input(
                            "Update Amount ($)",
                            min_value=0.0,
                            step=0.01,
                            value=current_amount,
                            format="%.2f",
                            key=f"edit_amount_{selected_id}"
                        )

                        # --------------------------------------------------
                        # PAYMENT DATE
                        # --------------------------------------------------

                        current_payment_date = (
                            selected_row["payment_date"]
                        )

                        if current_payment_date is None:

                            current_payment_date = date.today()

                        else:

                            # Convert pandas Timestamp /
                            # datetime to Python date
                            if hasattr(
                                current_payment_date,
                                "date"
                            ):

                                current_payment_date = (
                                    current_payment_date.date()
                                )

                            elif isinstance(
                                current_payment_date,
                                str
                            ):

                                try:

                                    current_payment_date = (
                                        date.fromisoformat(
                                            current_payment_date[:10]
                                        )
                                    )

                                except Exception:

                                    current_payment_date = (
                                        date.today()
                                    )

                        new_payment_date = st.date_input(
                            "Payment Date",
                            value=current_payment_date,
                            key=f"edit_payment_date_{selected_id}"
                        )

                        # --------------------------------------------------
                        # PERIOD
                        # --------------------------------------------------

                        current_period = (
                            str(
                                selected_row["period"]
                            )
                            if selected_row["period"] is not None
                            else ""
                        )

                        new_period = st.text_input(
                            "Period Paid For",
                            value=current_period,
                            key=f"edit_period_{selected_id}"
                        )

                        # --------------------------------------------------
                        # BUTTONS
                        # --------------------------------------------------

                        col1, col2 = st.columns(2)

                        update_sub = col1.form_submit_button(
                            "🔄 Update Payment"
                        )

                        delete_sub = col2.form_submit_button(
                            "🗑️ Delete Payment"
                        )

                        # ==================================================
                        # UPDATE PAYMENT
                        # ==================================================

                        if update_sub:

                            if new_amount <= 0:

                                st.error(
                                    "Payment amount must be greater than $0."
                                )

                            elif not new_period.strip():

                                st.error(
                                    "Please enter the period the payment is for."
                                )

                            else:

                                try:

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
                                            new_payment_date,
                                            new_period.strip(),
                                            selected_id
                                        )
                                    )

                                    st.cache_data.clear()

                                    st.success(
                                        "✅ Payment updated successfully!"
                                    )

                                    st.rerun()

                                except Exception as e:

                                    st.error(
                                        f"Error updating payment: {e}"
                                    )

                        # ==================================================
                        # DELETE PAYMENT
                        # ==================================================

                        if delete_sub:

                            try:

                                execute(
                                    """
                                    DELETE FROM payments
                                    WHERE id = %s
                                    """,
                                    (
                                        selected_id,
                                    )
                                )

                                st.cache_data.clear()

                                st.success(
                                    "✅ Payment deleted successfully!"
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    f"Error deleting payment: {e}"
                                )

        except Exception as e:

            st.error(
                f"Error loading payment management interface: {e}"
            )
