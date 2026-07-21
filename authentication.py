import pandas as pd

from database import query_dataframe

def login(username, password):

    query = """
    SELECT 
        username,
        role,
        id AS student_id
    FROM users
    WHERE username=?
    AND password=?
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
