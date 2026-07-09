import streamlit as st

from modules.students import student_management
from modules.payments import payment_management
from modules.homework import homework_management

from modules.scheduler import scheduler_management
from modules.attendance import attendance_management

from modules.reports import reports_management
from database import query_dataframe



def admin_page():


    st.sidebar.title(
        "Admin Control Panel"
    )


    option = st.sidebar.radio(

        "Choose Module",

        [
        "Dashboard",

        "Students",

        "Payments",

        "Homework",

        "Schedule",

        "Attendance",

        "Reports"
    ]

    )


    if option=="Dashboard":


        st.title(
            "Teacher Dashboard"
        )


        students=query_dataframe(
            """
            SELECT COUNT(*) AS total
            FROM students
            """
        )


        revenue=query_dataframe(
            """
            SELECT SUM(amount) AS total
            FROM payments
            """
        )


        sessions=query_dataframe(
            """
            SELECT COUNT(*) AS total
            FROM sessions
            """
        )


        col1,col2,col3=st.columns(3)


        col1.metric(
            "Students",
            int(students.iloc[0]["total"])
        )


        total=revenue.iloc[0]["total"]

        if total is None:
            total=0


        col2.metric(
            "Revenue",
            f"${total:,.2f}"
        )


        col3.metric(
            "Scheduled Sessions",
            int(sessions.iloc[0]["total"])
        )



    elif option=="Students":

        student_management()



    elif option=="Payments":

        payment_management()



    elif option=="Homework":

        homework_management()



    elif option=="Schedule":

        scheduler_management()


    elif option=="Attendance":

        attendance_management()



    elif option=="Reports":

        reports_management()