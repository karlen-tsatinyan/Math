from datetime import date
import pandas as pd
import streamlit as st

from database import execute, query_dataframe


def payment_management():
    st.header("💳 Payment Management")

    # Fetch active students (Fixed single quotes for string literal, no quotes on alias)
    students = query_dataframe(
        """
        SELECT
            id,
            first_name || ' ' || last_name AS name
        FROM students
        ORDER BY last_name
        """
    )

    if students.empty:
        st.warning("No students found. Please add students first.")
        return

    # Build safe student dropdown mapping
    student_options = {
        f"{row['name']} (ID: {row['id']})": row["id"]
        for _, row in students.iterrows()
    }

    # Session state index tracking
    saved_student_id = st.session_state.get("selected_student_id")
    default_index = 0

    if saved_student_id:
        for idx, (label, s_id) in enumerate(student_options.items()):
            if s_id == saved_student_id:
                default_index = idx
                break

    tab1, tab2, tab3 = st.tabs(["Add Payment", "Payment History", "Edit / Delete Payment"])

    # =========================================================
    # TAB 1: ADD PAYMENT
    # =========================================================
    with tab1:
        st.subheader("Record New Payment")

        selected_label = st.selectbox(
            "Select Student",
            options=list(student_options.keys()),
            index=default_index,
            key="add_payment_student_select"
        )

        student_id = student_options[selected_label]
        st.session_state.selected_student_id = student_id

        with st.form("add_payment_form", clear_on_submit=True):
            amount = st.number_input(
                "Payment Amount ($)",
                min_value=0.0,
                step=25.0,
                value=0.0
            )

            payment_date = st.date_input(
                "Payment Date",
                value=date.today()
            )

            period = st.text_input(
                "Payment Period",
                placeholder="Example: January Week 1, Term 2, etc."
            )

            notes = st.text_area(
                "Notes / Reference",
                placeholder="Check #, Bank Transfer ID, or special terms..."
            )

            submitted = st.form_submit_button("💾 Save Payment")

            if submitted:
                if amount <= 0:
                    st.error("Please enter a payment amount greater than 0.")
                else:
                    # Fixed: Changed ? placeholders to %%s for Supabase PostgreSQL
                    execute(
                        """
                        INSERT INTO payments (
                            student_id,
                            amount,
                            payment_date,
                            period,
                            notes
                        )
                        VALUES (%%s, %%s, %%s, %%s, %%s)
                        """,
                        (
                            student_id,
                            amount,
                            payment_date.isoformat(),
                            period.strip(),
                            notes.strip()
                        )
                    )
                    st.success("Payment successfully recorded!")
                    st.rerun()

    # =========================================================
    # TAB 2: PAYMENT HISTORY
    # =========================================================
    with tab2:
        st.subheader("All Payments")

        # Fixed: Changed single-quoted aliases to standard double quotes
        payments = query_dataframe(
            """
            SELECT
                p."id" AS "Payment ID",
                s."first_name" || ' ' || s."last_name" AS "Student",
                p."amount" AS "Amount",
                p."payment_date" AS "Date",
                p."period" AS "Period",
                p."notes" AS "Notes"
            FROM payments p
            JOIN students s ON p."student_id" = s."id"
            ORDER BY p."payment_date" DESC, p."id" DESC
            """
        )

        if payments.empty:
            st.info("No payment records recorded yet.")
        else:
            col1, col2 = st.columns([3, 1])

            with col2:
                total_revenue = payments["Amount"].sum()
                st.metric("Total Revenue", f"${total_revenue:,.2f}")

            with col1:
                st.dataframe(
                    payments,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Amount": st.column_config.NumberColumn(
                            "Amount",
                            format="$%.2f"
                        )
                    }
                )

    # =========================================================
    # TAB 3: EDIT / DELETE PAYMENT
    # =========================================================
    with tab3:
        st.subheader("Manage Existing Payments")

        edit_payments = query_dataframe(
            """
            SELECT
                p.id,
                s.first_name || ' ' || s.last_name AS student_name,
                p.amount,
                p.payment_date,
                p.period,
                p.notes
            FROM payments p
            JOIN students s ON p.student_id = s.id
            ORDER BY p.payment_date DESC, p.id DESC
            """
        )

        if edit_payments.empty:
            st.info("No payments available to edit.")
        else:
            payment_map = {
                f"#{row['id']} - {row['student_name']} (${row['amount']:.2f} on {row['payment_date']})": row["id"]
                for _, row in edit_payments.iterrows()
            }

            selected_payment_label = st.selectbox(
                "Select Payment Entry to Modify",
                options=list(payment_map.keys())
            )

            payment_id = payment_map[selected_payment_label]
            payment = edit_payments[edit_payments["id"] == payment_id].iloc[0]

            col_edit, col_del = st.columns([3, 1])

            with col_edit:
                amount = st.number_input(
                    "Payment Amount ($)",
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

                btn_cols = st.columns([1, 1])

                with btn_cols[0]:
                    if st.button("💾 Update Payment", type="primary"):
                        # Fixed: Changed SQLite ? to PostgreSQL %%s placeholders
                        execute(
                            """
                            UPDATE payments
                            SET
                                amount = %%s,
                                payment_date = %%s,
                                period = %%s,
                                notes = %%s
                            WHERE id = %%s
                            """,
                            (
                                amount,
                                payment_date.isoformat(),
                                period.strip(),
                                notes.strip(),
                                int(payment_id)
                            )
                        )
                        st.success("Payment updated successfully.")
                        st.rerun()

                with btn_cols[1]:
                    if st.button("🗑️ Delete Payment"):
                        # Fixed: Changed SQLite ? to PostgreSQL %%s placeholders
                        execute("DELETE FROM payments WHERE id = %%s", (int(payment_id),))
                        st.success("Payment deleted successfully.")
                        st.rerun()
