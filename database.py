import pandas as pd
import numpy as np
import psycopg2
import streamlit as st


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
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create a PostgreSQL connection using the Supabase
    connection URL stored in Streamlit secrets.
    """

    return psycopg2.connect(
        st.secrets["postgres"]["url"]
    )


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
        st.error(str(e))

        print("QUERY:")
        print(query)

        print("PARAMS:")
        print(params)

        raise e

    finally:

        if conn is not None:

            conn.close()


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

            conn.close()


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

            conn.close()


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

            conn.close()


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

            conn.close()
