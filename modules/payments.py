import streamlit as st
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
            execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
        except Exception:
            pass

def payment_management():
    # Automatically patch any missing columns in the database table
    ensure_payments_schema()

    st.title("💰 Payment Management")

    # Re-introducing your multi-tab layout
    tab1, tab2, tab3 = st.tabs(["💳 Payment History", "➕ Record Payment", "✏️ Edit / Manage Payments"])

    # ==========================
    # TAB 1: Payment History
    # ==========================
    with tab1:
        st.subheader("Payment Records")
        try:
            payments = query_dataframe(
                """
                SELECT 
                    p.id,
                    p.student_id,
                    COALESCE(p.amount, 0.00) AS amount,
                    COALESCE(p.payment_date, CURRENT_DATE) AS payment_date,
                    COALESCE(p.period, '') AS period
                FROM payments p
                ORDER BY p.payment_date DESC
                """
            )
            if not payments.empty:
                st.dataframe(payments, use_container_width=True)
            else:
                st.info("No payment records found.")
        except Exception as e:
            st.error(f"Error loading payment history: {e}")

    # ==========================
    # TAB 2: Record Payment
    # ==========================
    with tab2:
        st.subheader("Record New Payment")
        with st.form("payment_form"):
            student_id_input = st.number_input("Student ID", min_value=1, step=1)
            amount_input = st.number_input("Amount ($)", min_value=0.0, format="%.2f")
            period_input = st.text_input("Period (e.g., June 2026)")
            
            submitted = st.form_submit_button("💾 Save Payment")
            if submitted:
                try:
                    execute(
                        """
                        INSERT INTO payments (student_id, amount, period, payment_date)
                        VALUES (%s, %s, %s, CURRENT_DATE)
                        """,
                        (student_id_input, amount_input, period_input)
                    )
                    st.success("Payment successfully recorded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving payment: {e}")

    # ==========================
    # TAB 3: Edit / Manage Payments
    # ==========================
    with tab3:
        st.subheader("Edit or Remove Payment Entries")
        try:
            payments_list = query_dataframe("SELECT id, student_id, amount, period FROM payments ORDER BY id DESC")
            if not payments_list.empty:
                payment_options = {f"ID {row['id']} - Student {row['student_id']} (${row['amount']})": row['id'] for _, row in payments_list.iterrows()}
                selected_label = st.selectbox("Select Payment to Edit", list(payment_options.keys()))
                
                if selected_label:
                    selected_id = payment_options[selected_label]
                    selected_row = payments_list[payments_list['id'] == selected_id].iloc[0]
                    
                    with st.form("edit_payment_form"):
                        new_amount = st.number_input("Update Amount ($)", value=float(selected_row['amount']), format="%.2f")
                        new_period = st.text_input("Update Period", value=str(selected_row['period'] or ''))
                        
                        col1, col2 = st.columns(2)
                        update_sub = col1.form_submit_button("🔄 Update Payment")
                        delete_sub = col2.form_submit_button("🗑️ Delete Payment")
                        
                        if update_sub:
                            execute(
                                "UPDATE payments SET amount = %s, period = %s WHERE id = %s",
                                (new_amount, new_period, selected_id)
                            )
                            st.success("Payment updated successfully!")
                            st.rerun()
                            
                        if delete_sub:
                            execute("DELETE FROM payments WHERE id = %s", (selected_id,))
                            st.success("Payment deleted successfully!")
                            st.rerun()
            else:
                st.info("No payments available to edit.")
        except Exception as e:
            st.error(f"Error loading management interface: {e}")
