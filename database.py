```python
import pandas as pd
import numpy as np
import psycopg2
import streamlit as st
from psycopg2 import pool


# ============================================================
# PARAMETER CONVERSION
# ============================================================

def convert_params(params):
    """
    Convert NumPy/Pandas numeric values into
    native Python types that psycopg2 can handle.
    """

    if params is None:
        return ()

    return tuple(
        int(x) if isinstance(x, np.integer) else x
        for x in params
    )


# ============================================================
# SUPABASE CONNECTION POOL
# ============================================================

@st.cache_resource
def get_connection_pool():
    """
    Create one reusable PostgreSQL connection pool.

    This prevents the application from opening a brand-new
    Supabase connection for every database query.
    """

    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=st.secrets["postgres"]["url"]
    )


def get_connection():
    """
    Get an available connection from the pool.
    """

    connection_pool = get_connection_pool()

    return connection_pool.getconn()


def release_connection(conn):
    """
    Return the connection to the pool.
    """

    if conn is not None:

        connection_pool = get_connection_pool()

        connection_pool.putconn(conn)


# ============================================================
# QUERY DATAFRAME
# ============================================================

def query_dataframe(query, params=()):

    params = convert_params(params)

    conn = None

    try:

        conn = get_connection()

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

            if cur.description:

                columns = [
                    desc[0]
                    for desc in cur.description
                ]

                data = cur.fetchall()

                return pd.DataFrame(
                    data,
                    columns=columns
                )

            return pd.DataFrame()

    except Exception as e:

        if conn is not None:

            try:
                conn.rollback()
            except Exception:
                pass

        print("DATABASE ERROR:")
        print(e)

        print("QUERY:")
        print(query)

        print("PARAMS:")
        print(params)

        raise e

    finally:

        if conn is not None:

            release_connection(conn)


# ============================================================
# EXECUTE
# ============================================================

def execute(query, params=()):

    params = convert_params(params)

    conn = None

    try:

        conn = get_connection()

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

        conn.commit()

    except Exception as e:

        if conn is not None:

            try:
                conn.rollback()
            except Exception:
                pass

        raise e

    finally:

        if conn is not None:

            release_connection(conn)


# ============================================================
# GET SINGLE ROW
# ============================================================

def get_single(query, params=()):

    params = convert_params(params)

    conn = None

    try:

        conn = get_connection()

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

            return cur.fetchone()

    except Exception as e:

        if conn is not None:

            try:
                conn.rollback()
            except Exception:
                pass

        raise e

    finally:

        if conn is not None:

            release_connection(conn)


# ============================================================
# EXECUTE MANY
# ============================================================

def execute_many(query, data):

    converted_data = [
        convert_params(row)
        for row in data
    ]

    conn = None

    try:

        conn = get_connection()

        with conn.cursor() as cur:

            cur.executemany(
                query,
                converted_data
            )

        conn.commit()

    except Exception as e:

        if conn is not None:

            try:
                conn.rollback()
            except Exception:
                pass

        raise e

    finally:

        if conn is not None:

            release_connection(conn)


# ============================================================
# EXECUTE RETURNING
# ============================================================

def execute_returning(query, params=()):

    params = convert_params(params)

    conn = None

    try:

        conn = get_connection()

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

            row = cur.fetchone()

        conn.commit()

        return row

    except Exception as e:

        if conn is not None:

            try:
                conn.rollback()
            except Exception:
                pass

        raise e

    finally:

        if conn is not None:

            release_connection(conn)
```
