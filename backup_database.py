import sqlite3
import pandas as pd
import streamlit as st
from config import DATABASE_NAME


def get_connection():
    """
    Establishes and returns a connection to the SQLite database.
    Enforces Foreign Key constraints for relational integrity.
    """
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute(query: str, params: tuple = ()) -> None:
    """
    Executes a write operation (INSERT, UPDATE, DELETE) safely using context managers.
    
    Args:
        query (str): The SQL command to execute.
        params (tuple): Parameters to inject safely into the query.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database Write Error: {e}")
        raise e


def query_dataframe(query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Executes a SELECT query and returns the results as a Pandas DataFrame.
    
    Args:
        query (str): The SQL SELECT statement.
        params (tuple): Parameters to inject safely into the query.
        
    Returns:
        pd.DataFrame: Query results formatted for Streamlit displays.
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except sqlite3.Error as e:
        st.error(f"Database Read Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def query_one(query: str, params: tuple = ()):
    """
    Fetches a single record from the database.
    
    Args:
        query (str): The SQL SELECT query.
        params (tuple): Parameters for query bindings.
        
    Returns:
        sqlite3.Row or tuple or None: First match row or None.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        conn.close()
