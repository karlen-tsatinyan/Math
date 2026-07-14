import sqlite3
import pandas as pd

from config import DATABASE_NAME



def get_connection():

    conn = sqlite3.connect(
        DATABASE_NAME
    )

    conn.row_factory = sqlite3.Row

    return conn



def execute(query, params=()):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        query,
        params
    )

    conn.commit()

    conn.close()



def execute_many(query, data):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.executemany(
        query,
        data
    )

    conn.commit()

    conn.close()



def query_dataframe(query, params=()):

    conn = get_connection()

    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )

    conn.close()

    return df



def get_single(query, params=()):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        query,
        params
    )

    result = cursor.fetchone()

    conn.close()

    return result
