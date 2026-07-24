import pandas as pd
import psycopg2
import streamlit as st


def get_connection():

    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
    )


def query_dataframe(query, params=()):

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

        raise e

    finally:

        conn.close()



def execute(query, params=()):

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

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.executemany(
                query,
                data
            )

        conn.commit()


    except Exception as e:

        conn.rollback()
        raise e


    finally:

        conn.close()
        

def execute_returning(query, params=()):

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


