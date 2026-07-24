from database import query_dataframe


def login(username, password):

    query = """
    SELECT
        username,
        role,
        student_id
    FROM users
    WHERE username=%s
    AND password=%s
    """

    result = query_dataframe(
        query,
        (
            username,
            password
        )
    )

    if len(result) == 1:

        return {
            "username": result.iloc[0]["username"],
            "role": result.iloc[0]["role"],
            "student_id": result.iloc[0]["student_id"]
        }

    return None
