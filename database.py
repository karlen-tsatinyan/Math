import psycopg2
import pandas as pd
import streamlit as st


def get_connection():

    return psycopg2.connect(
        st.secrets["postgres"]["url"]
    )


def execute(query, params=()):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            query,
            params
        )

        conn.commit()

        cursor.close()

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()



def execute_many(query, data):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.executemany(
            query,
            data
        )

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

        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        return df


    except Exception as e:

        print("SQL ERROR:")
        print(e)

        print("QUERY:")
        print(query)

        print("PARAMS:")
        print(params)

        raise e


    finally:

        conn.close()



def get_single(query, params=()):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            query,
            params
        )

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

        cursor.execute(
            query,
            params
        )

        row = cursor.fetchone()

        conn.commit()

        cursor.close()

        return row


    except Exception as e:

        conn.rollback()
        raise e


    finally:

        conn.close()
