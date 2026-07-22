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

    # Safe query matching your PostgreSQL schema with fallback handlers
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

    st.divider()
    st.subheader("➕ Record / Update Payment")
    
    # Simple form wrapper for adding or managing payments
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
