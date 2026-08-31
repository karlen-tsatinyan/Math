from database import query_dataframe


def login(username, password):

    # ==========================================================
    # FIND USER
    # ==========================================================

    query = """
        SELECT
            u.username,
            u.role,
            u.student_id
        FROM users u
        WHERE LOWER(TRIM(u.username)) = LOWER(TRIM(%s))
          AND u.password = %s
    """

    result = query_dataframe(
        query,
        (
            username.strip(),
            password
        )
    )

    # ==========================================================
    # INVALID LOGIN
    # ==========================================================

    if len(result) != 1:
        return None

    user = {
        "username": result.iloc[0]["username"],
        "role": result.iloc[0]["role"],
        "student_id": result.iloc[0]["student_id"]
    }

    # ==========================================================
    # ADMIN LOGIN
    # ==========================================================

    if user["role"] == "admin":
        user["courses"] = []
        user["selected_course"] = None

        return user

    # ==========================================================
    # STUDENT LOGIN
    #
    # Get the courses assigned to this student.
    #
    # For now, courses are read from the student's
    # "subject" field.
    # ==========================================================

    student_id = user["student_id"]

    course_query = """
        SELECT
            subject
        FROM students
        WHERE id = %s
        LIMIT 1
    """

    student_result = query_dataframe(
        course_query,
        (student_id,)
    )

    courses = []

    if not student_result.empty:

        subject = student_result.iloc[0]["subject"]

        if (
            subject is not None
            and str(subject).strip()
            and str(subject).strip().lower() not in [
                "nan",
                "none"
            ]
        ):

            # --------------------------------------------------
            # Allow multiple courses separated by commas.
            #
            # Example:
            #
            # Algebra, Geometry
            # --------------------------------------------------

            courses = [
                course.strip()
                for course in str(subject).split(",")
                if course.strip()
            ]

    # ==========================================================
    # REMOVE DUPLICATES
    # ==========================================================

    courses = list(
        dict.fromkeys(courses)
    )

    # ==========================================================
    # STORE COURSES IN USER
    # ==========================================================

    user["courses"] = courses

    # ==========================================================
    # ONE COURSE
    #
    # Automatically select it.
    # No course-selection screen will be necessary.
    # ==========================================================

    if len(courses) == 1:

        user["selected_course"] = courses[0]

    else:

        user["selected_course"] = None

    return user
