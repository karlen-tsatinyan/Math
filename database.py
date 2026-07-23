import psycopg2
import pandas as pd
import streamlit as st

def get_connection():
    # Reads the secret connection string safely from Streamlit Secrets
    conn = psycopg2.connect(st.secrets["postgres"]["url"])
    return conn

def execute(query, params=()):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query_pg = query.replace("?", "%s")
        cursor.execute(query_pg, params)
        conn.commit()
        cursor.close()
    except Exception as e:
        conn.rollback()  # Roll back transaction on error so it doesn't block future queries
        raise e
    finally:
        conn.close()

def execute_many(query, data):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query_pg = query.replace("?", "%s")
        cursor.executemany(query_pg, data)
        conn.commit()
        cursor.close()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@st.cache_data(ttl=600)
def query_dataframe(query, params=()):
    conn = get_connection()
    try:
        query_pg = query.replace("?", "%s")
        df = pd.read_sql_query(query_pg, conn, params=params)
        return df
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_single(query, params=()):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query_pg = query.replace("?", "%s")
        cursor.execute(query_pg, params)
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_returning(query, params=()):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        query_pg = query.replace("?", "%s")

        cursor.execute(query_pg, params)

        row = cursor.fetchone()

        conn.commit()

        cursor.close()

        return row

    except Exception as e:

        conn.rollback()

        raise e

    finally:

        conn.close()
