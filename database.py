import pandas as pd
import numpy as np
import psycopg2
import streamlit as st


def convert_params(params):
    """
    Convert numpy data types from Pandas into
    native Python types for psycopg2.
    """

    if params is None:
        return ()

    return tuple(
        int(x) if isinstance(x, np.integer) else x
        for x in params
    )


def get_connection():

    return psycopg2.connect(
        st.secrets["postgres"]["url"]
    )


def query_dataframe(query, params=()):

    params = convert_params(params)

    conn = get_connection()

    try:

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

        st.error(f"Database Error: {e}")
        raise e

    finally:

        conn.close()



def execute(query, params=()):

    params = convert_params(params)

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

        conn.commit()

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()



def get_single(query, params=()):

    params = convert_params(params)

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

            return cur.fetchone()

    except Exception as e:

        raise e

    finally:

        conn.close()



def execute_many(query, data):

    # Convert every row
    converted_data = [
        convert_params(row)
        for row in data
    ]

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.executemany(
                query,
                converted_data
            )

        conn.commit()

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()



def execute_returning(query, params=()):

    params = convert_params(params)

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                query,
                params
            )

            row = cur.fetchone()

        conn.commit()

        return row

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()
