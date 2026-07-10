import sqlite3

from config import DATABASE_NAME


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


def execute(sql):
    conn = get_connection()

    cursor = conn.cursor()

    cursor.executescript(sql)

    conn.commit()

    conn.close()