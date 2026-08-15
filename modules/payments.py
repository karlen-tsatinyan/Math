import streamlit as st
from datetime import date
from database import execute, query_dataframe


# ============================================================
# ENSURE PAYMENTS SCHEMA
# ============================================================

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


# ============================================================
# PAYMENT MANAGEMENT
# ============================================================

def payment_management():
    st.error("🚨 THIS IS THE PAYMENT_MANAGEMENT FUNCTION I AM RUNNING")
    st.sidebar.warning("PAYMENT VERSION: NEW")

    # --------------------------------------------------------
    # ENSURE PAYMENT SCHEMA
    # --------------------------------------------------------

    ensure_payments_schema()

    st.title("💰 Payment Management")

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "💳 Payment History",
            "➕ Record Payment",
            "✏️ Edit / Manage Payments"
        ]
    )

    # ========================================================
    # TAB 1 — PAYMENT HISTORY
    # ========================================================

    with tab1:

        st.subheader("💳 Payment Records")

        try:

            payments = query_dataframe(
                """
                SELECT

                    p.id,

                    p.student_id,

                    s.first_name || ' ' || s.last_name
                        AS student_name,

                    COALESCE(
                        p.amount,
                        0.00
                    ) AS amount,

                    p.payment_date,

                    COALESCE(
                        p.period,
                        ''
                    ) AS period,

                    COALESCE(
                        p.status,
                        'Completed'
                    ) AS status

                FROM payments p

                JOIN students s
                    ON p.student_id = s.id

                ORDER BY
                    p.payment_date DESC,
                    p.id DESC
                """
            )

            if payments.empty:

                st.info(
                    "No payment records found."
                )

            else:

                # ------------------------------------------------
                # FORMAT PAYMENT DATE FOR DISPLAY
                # ------------------------------------------------

                payments["payment_date"] = (
                    payments["payment_date"]
                    .apply(
                        lambda x:
                            convert_to_date(x).strftime("%b %d, %Y")
                            if pd_is_valid_date(x)
                            else ""
                    )
                )

                # ------------------------------------------------
                # DISPLAY COLUMN NAMES
                # ------------------------------------------------

                display_payments = payments.rename(
                    columns={
                        "id": "Payment ID",
                        "student_id": "Student ID",
                        "student_name": "Student",
                        "amount": "Amount",
                        "payment_date": "Payment Date",
                        "period": "Period Paid For",
                        "status": "Status"
                    }
                )

                # ------------------------------------------------
                # DISPLAY
                # ------------------------------------------------

                st.dataframe(
                    display_payments[
                        [
                            "Payment ID",
                            "Student ID",
                            "Student",
                            "Amount",
                            "Payment Date",
                            "Period Paid For",
                            "Status"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={

                        "Payment ID": st.column_config.NumberColumn(
                            "Payment ID"
                        ),

                        "Student ID": st.column_config.NumberColumn(
                            "Student ID"
                        ),

                        "Amount": st.column_config.NumberColumn(
                            "Amount",
                            format="$%.2f"
                        ),

                        "Payment Date": st.column_config.TextColumn(
                            "Payment Date"
                        )
                    }
                )

        except Exception as e:

            st.error(
                f"Error loading payment history: {e}"
            )

    # ========================================================
    # TAB 2 — RECORD PAYMENT
    # ========================================================

    with tab2:

        st.subheader(
            "➕ Record New Payment"
        )

        # ----------------------------------------------------
        # GET ACTIVE STUDENTS
        # ----------------------------------------------------

        students = query_dataframe(
            """
            SELECT

                id,

                first_name || ' ' || last_name
                    AS name

            FROM students

            WHERE COALESCE(archived, 0) = 0

            ORDER BY
                last_name,
                first_name
            """
        )

        if students.empty:

            st.warning(
                "No active students available."
            )

        else:
            st.subheader("➕ Record New Payment")

            st.error("🚨 PAYMENT FORM — NEW CODE IS RUNNING")

            with st.form("payment_form"):

                st.write("### Test Payment Form")
            
                student_name = st.selectbox(
                    "Student",
                    students["name"].tolist(),
                    key="payment_student_select"
                )
            
                amount_input = st.number_input(
                    "💵 Amount ($)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="payment_amount"
                )
            
                st.write("### PAYMENT DATE TEST")
            
                payment_date_input = st.date_input(
                    "📅 Payment Date",
                    value=date.today(),
                    format="MM/DD/YYYY",
                    key="payment_date_input"
                )
            
                st.write(
                    f"Selected date: {payment_date_input}"
                )
            
                period_input = st.text_input(
                    "📆 Period Paid For",
                    placeholder="e.g. June 2026",
                    key="payment_period"
                )
            
                status_input = st.selectbox(
                    "📌 Payment Status",
                    [
                        "Completed",
                        "Pending",
                        "Refunded"
                    ],
                    key="payment_status"
                )
            
                submitted = st.form_submit_button(
                    "💾 Save Payment",
                    use_container_width=True
                )

                if submitted:

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
                                %s
                            )
                            """,
                            (
                                student_id_input,
                                amount_input,
                                payment_date_input,
                                period_input.strip(),
                                status_input
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

    # ========================================================
    # TAB 3 — EDIT / MANAGE PAYMENTS
    # ========================================================

    with tab3:

        st.subheader(
            "✏️ Edit or Remove Payment Entries"
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

                    COALESCE(
                        p.status,
                        'Completed'
                    ) AS status

                FROM payments p

                JOIN students s
                    ON p.student_id = s.id

                ORDER BY
                    p.payment_date DESC,
                    p.id DESC
                """
            )

            if payments_list.empty:

                st.info(
                    "No payments available to edit."
                )

            else:

                # --------------------------------------------
                # PAYMENT SELECTOR
                # --------------------------------------------

                payment_options = {}

                for _, row in payments_list.iterrows():

                    student = str(
                        row["student_name"]
                    )

                    amount = float(
                        row["amount"] or 0
                    )

                    period = str(
                        row["period"] or ""
                    )

                    raw_date = row["payment_date"]

                    if pd_is_valid_date(raw_date):

                        display_date = (
                            convert_to_date(
                                raw_date
                            ).strftime(
                                "%b %d, %Y"
                            )
                        )

                    else:

                        display_date = "No Date"

                    label = (
                        f"{student} | "
                        f"${amount:,.2f} | "
                        f"{display_date} | "
                        f"{period}"
                    )

                    payment_options[label] = row["id"]

                selected_label = st.selectbox(
                    "Select Payment to Edit",
                    list(
                        payment_options.keys()
                    ),
                    key="edit_payment_selector"
                )

                selected_id = payment_options[
                    selected_label
                ]

                selected_row = payments_list[
                    payments_list["id"] == selected_id
                ].iloc[0]

                # --------------------------------------------
                # CURRENT VALUES
                # --------------------------------------------

                current_amount = float(
                    selected_row["amount"] or 0
                )

                current_period = str(
                    selected_row["period"] or ""
                )

                current_status = str(
                    selected_row["status"] or "Completed"
                )

                # --------------------------------------------
                # CURRENT PAYMENT DATE
                # --------------------------------------------

                raw_payment_date = (
                    selected_row["payment_date"]
                )

                if pd_is_valid_date(
                    raw_payment_date
                ):

                    current_payment_date = (
                        convert_to_date(
                            raw_payment_date
                        )
                    )

                else:

                    current_payment_date = date.today()

                # --------------------------------------------
                # EDIT FORM
                # --------------------------------------------

                with st.form(
                    "edit_payment_form"
                ):

                    st.write(
                        f"**Student:** {selected_row['student_name']}"
                    )
                    
                    # ----------------------------------------
                    # AMOUNT
                    # ----------------------------------------
                    
                    new_amount = st.number_input(
                        "💵 Amount ($)",
                        min_value=0.0,
                        value=current_amount,
                        step=0.01,
                        format="%.2f",
                        key=f"edit_amount_{selected_id}"
                    )
                    
                    # ----------------------------------------
                    # PAYMENT DATE
                    # ----------------------------------------
                    
                    new_payment_date = st.date_input(
                        "📅 Payment Date",
                        value=current_payment_date,
                        format="MM/DD/YYYY",
                        key=f"edit_payment_date_{selected_id}"
                    )
                    
                    # ----------------------------------------
                    # PERIOD
                    # ----------------------------------------
                    
                    new_period = st.text_input(
                        "📆 Period Paid For",
                        value=current_period,
                        key=f"edit_period_{selected_id}"
                    )
                    
                    # ----------------------------------------
                    # STATUS
                    # ----------------------------------------
                    
                    status_options = [
                        "Completed",
                        "Pending",
                        "Refunded"
                    ]
                    
                    if current_status not in status_options:
                        current_status = "Completed"
                    
                    new_status = st.selectbox(
                        "📌 Payment Status",
                        status_options,
                        index=status_options.index(current_status),
                        key=f"edit_status_{selected_id}"
                    )

                    st.divider()

                    col1, col2 = st.columns(2)

                    update_sub = col1.form_submit_button(
                        "🔄 Update Payment",
                        use_container_width=True
                    )

                    delete_sub = col2.form_submit_button(
                        "🗑️ Delete Payment",
                        use_container_width=True
                    )

                    # ========================================
                    # UPDATE PAYMENT
                    # ========================================

                    if update_sub:

                        try:

                            execute(
                                """
                                UPDATE payments

                                SET

                                    amount = %s,

                                    payment_date = %s,

                                    period = %s,

                                    status = %s

                                WHERE id = %s
                                """,
                                (
                                    new_amount,
                                    new_payment_date,
                                    new_period.strip(),
                                    new_status,
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

                    # ========================================
                    # DELETE PAYMENT
                    # ========================================

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
                f"Error loading management interface: {e}"
            )


# ============================================================
# DATE HELPERS
# ============================================================

def pd_is_valid_date(value):
    """
    Check whether a database value can safely
    be interpreted as a date.
    """

    if value is None:
        return False

    try:

        if hasattr(value, "date"):

            return True

        text = str(value).strip()

        if not text:
            return False

        parts = text.split("-")

        return len(parts) == 3

    except Exception:

        return False


def convert_to_date(value):
    """
    Convert PostgreSQL/Pandas/string date
    into a Python date.
    """

    if hasattr(value, "date"):

        try:
            return value.date()
        except Exception:
            pass

    if isinstance(value, date):

        return value

    text = str(value).strip()

    try:

        return date.fromisoformat(
            text[:10]
        )

    except Exception:

        return date.today()
