import pandas as pd
import psycopg2
import streamlit as st


def get_connection():
    """
    Establishes and returns a connection to the PostgreSQL database
    using Streamlit secrets.
    """
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
    )


def query_dataframe(query, params=None):
    """
    Executes a SELECT query safely using psycopg2 directly and loads the output
    into a Pandas DataFrame without throwing pd.read_sql parameter parsing errors.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                return pd.DataFrame(data, columns=columns)
            return pd.DataFrame()
    except Exception as e:
        raise e
    finally:
        conn.close()


def execute(query, params=None):
    """
    Executes INSERT, UPDATE, or DELETE queries with automatic transaction commit.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
