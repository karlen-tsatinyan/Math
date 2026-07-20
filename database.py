import psycopg2
import pandas as pd
import streamlit as st

def get_connection():
    # Reads the secret connection string safely from Streamlit Secrets
    conn = psycopg2.connect(st.secrets["postgres"]["url"])
    return conn

def execute(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    # Replace SQLite '?' placeholder with Postgres '%s' placeholder if needed
    query_pg = query.replace("?", "%s")
    cursor.execute(query_pg, params)
    conn.commit()
    cursor.close()
    conn.close()

def execute_many(query, data):
    conn = get_connection()
    cursor = conn.cursor()
    query_pg = query.replace("?", "%s")
    cursor.executemany(query_pg, data)
    conn.commit()
    cursor.close()
    conn.close()

def query_dataframe(query, params=()):
    conn = get_connection()
    query_pg = query.replace("?", "%s")
    df = pd.read_sql_query(query_pg, conn, params=params)
    conn.close()
    return df

def get_single(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    query_pg = query.replace("?", "%s")
    cursor.execute(query_pg, params)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
