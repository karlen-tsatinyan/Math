import streamlit as st
import pandas as pd
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

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

    st.title("💰 Financial Statements")

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
    # Lock Button
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

    # --------------------------------------------------------
    # Clean Payment Data
    # --------------------------------------------------------

    payments["amount"] = pd.to_numeric(
        payments["amount"],
        errors="coerce"
    ).fillna(0)

    payments["payment_date"] = pd.to_datetime(
        payments["payment_date"],
        errors="coerce"
    )

    # ========================================================
    # DATE FILTER
    # ========================================================

    st.subheader("📅 Filter Statement")

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        start_date = st.date_input(
            "Start Date",
            value=None,
            format="MM/DD/YYYY",
            key=f"financial_start_date_{student_id}"
        )

    with filter_col2:

        end_date = st.date_input(
            "End Date",
            value=None,
            format="MM/DD/YYYY",
            key=f"financial_end_date_{student_id}"
        )

    # --------------------------------------------------------
    # Validate Date Range
    # --------------------------------------------------------

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):

        st.error(
            "⚠️ Start Date cannot be later than End Date."
        )

        return

    # --------------------------------------------------------
    # Apply Date Filter
    # --------------------------------------------------------

    filtered_payments = payments.copy()

    if start_date is not None:

        filtered_payments = filtered_payments[
            filtered_payments["payment_date"].dt.date
            >= start_date
        ]

    if end_date is not None:

        filtered_payments = filtered_payments[
            filtered_payments["payment_date"].dt.date
            <= end_date
        ]

    # --------------------------------------------------------
    # Filter Information
    # --------------------------------------------------------

    if (
        start_date is not None
        and end_date is not None
    ):

        st.caption(
            f"Showing payments from "
            f"**{start_date.strftime('%m/%d/%Y')}** "
            f"through "
            f"**{end_date.strftime('%m/%d/%Y')}**."
        )

    elif start_date is not None:

        st.caption(
            f"Showing payments from "
            f"**{start_date.strftime('%m/%d/%Y')}** onward."
        )

    elif end_date is not None:

        st.caption(
            f"Showing payments through "
            f"**{end_date.strftime('%m/%d/%Y')}**."
        )

    else:

        st.caption(
            "Showing all payment records."
        )

    # --------------------------------------------------------
    # No Results
    # --------------------------------------------------------

    if filtered_payments.empty:

        st.warning(
            "No payment records found for the selected date range."
        )

        return

    # ========================================================
    # SUMMARY
    # ========================================================

    total_paid = filtered_payments[
        "amount"
    ].sum()

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "💵 Total Paid",
            f"${total_paid:,.2f}"
        )

    with c2:

        st.metric(
            "🧾 Payments",
            len(filtered_payments)
        )

    st.divider()

    # ========================================================
    # STATEMENT
    # ========================================================

    st.subheader(
        "📄 Statement of Account"
    )

    display = filtered_payments.copy()

    # --------------------------------------------------------
    # Format Date
    # --------------------------------------------------------

    display["payment_date"] = display[
        "payment_date"
    ].apply(
        lambda x:
            x.strftime("%m/%d/%Y")
            if pd.notna(x)
            else ""
    )

    # --------------------------------------------------------
    # Rename Columns
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Format Amount
    # --------------------------------------------------------

    display["Amount"] = display[
        "Amount"
    ].apply(
        lambda x: f"${x:,.2f}"
    )

    st.dataframe(
        display[
            [
                "Payment Date",
                "Amount",
                "Period",
                "Status"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ========================================================
    # DOWNLOADS
    # ========================================================

    st.subheader(
        "⬇️ Download Statement"
    )

    # --------------------------------------------------------
    # Download Data
    # --------------------------------------------------------

    download_data = filtered_payments.copy()

    download_data["payment_date"] = (
        download_data["payment_date"]
        .apply(
            lambda x:
                x.strftime("%m/%d/%Y")
                if pd.notna(x)
                else ""
        )
    )

    download_data = download_data.rename(
        columns={
            "payment_date": "Payment Date",
            "amount": "Amount",
            "period": "Period",
            "status": "Status"
        }
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------
    
    pdf_buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    elements = []
    
    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------
    
    elements.append(
        Paragraph(
            "Financial Statement",
            styles["Title"]
        )
    )
    
    elements.append(
        Paragraph(
            "Advanced Math Tutoring Portal",
            styles["Normal"]
        )
    )
    
    elements.append(Spacer(1, 10))
    
    # --------------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------------
    
    if start_date is not None and end_date is not None:
    
        date_text = (
            f"Statement Period: "
            f"{start_date.strftime('%m/%d/%Y')} "
            f"to "
            f"{end_date.strftime('%m/%d/%Y')}"
        )
    
    elif start_date is not None:
    
        date_text = (
            f"Statement Period: "
            f"{start_date.strftime('%m/%d/%Y')} onward"
        )
    
    elif end_date is not None:
    
        date_text = (
            f"Statement Period: "
            f"Through {end_date.strftime('%m/%d/%Y')}"
        )
    
    else:
    
        date_text = "Statement Period: All Payments"
    
    
    elements.append(
        Paragraph(
            date_text,
            styles["Normal"]
        )
    )
    
    elements.append(Spacer(1, 15))
    
    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    
    summary_data = [
        ["Total Paid", "Number of Payments"],
        [
            f"${total_paid:,.2f}",
            str(len(filtered_payments))
        ]
    ]
    
    summary_table = Table(
        summary_data,
        colWidths=[
            2.5 * 72,
            2.5 * 72
        ]
    )
    
    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )
    
    elements.append(summary_table)
    
    elements.append(Spacer(1, 20))
    
    # --------------------------------------------------------
    # PAYMENT TABLE
    # --------------------------------------------------------
    
    elements.append(
        Paragraph(
            "Payment History",
            styles["Heading2"]
        )
    )
    
    pdf_data = [
        [
            "Payment Date",
            "Amount",
            "Period",
            "Status"
        ]
    ]
    
    for _, row in download_data.iterrows():
    
        pdf_data.append([
            str(row["Payment Date"]),
            f"${float(row['Amount']):,.2f}",
            str(row["Period"]),
            str(row["Status"])
        ])
    
    payment_table = Table(
        pdf_data,
        colWidths=[
            1.3 * 72,
            1.1 * 72,
            2.0 * 72,
            1.2 * 72
        ],
        repeatRows=1
    )
    
    payment_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "ALIGN",
                (1, 1),
                (1, -1),
                "RIGHT"
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )
    
    elements.append(payment_table)
    
    elements.append(Spacer(1, 20))
    
    elements.append(
        Paragraph(
            "🔒 Financial information is protected by Parent PIN authentication.",
            styles["Normal"]
        )
    )
    
    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------
    
    doc.build(elements)
    
    pdf_buffer.seek(0)
    
    st.download_button(
        "📄 Download PDF",
        data=pdf_buffer.getvalue(),
        file_name="financial_statement.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    try:

        buffer = BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl"
        ) as writer:

            download_data[
                [
                    "Payment Date",
                    "Amount",
                    "Period",
                    "Status"
                ]
            ].to_excel(
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
            ),
            use_container_width=True
        )

    except Exception:

        pass

    st.caption(
        "🔒 Financial information is protected by Parent PIN authentication."
    )
