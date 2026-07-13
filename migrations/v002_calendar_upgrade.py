import sqlite3

from config import DATABASE_NAME


def column_exists(cursor, table_name, column_name):

    cursor.execute(f"PRAGMA table_info({table_name})")

    columns = [row[1] for row in cursor.fetchall()]

    return column_name in columns


def migrate():

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    # --------------------------
    # students.active
    # --------------------------

    if not column_exists(cursor, "students", "active"):

        cursor.execute("""

            ALTER TABLE students

            ADD COLUMN active INTEGER DEFAULT 1

        """)

    # --------------------------
    # sessions.recurring_group
    # --------------------------

    if not column_exists(cursor, "sessions", "recurring_group"):

        cursor.execute("""

            ALTER TABLE sessions

            ADD COLUMN recurring_group TEXT

        """)

    # --------------------------
    # sessions.color
    # --------------------------

    if not column_exists(cursor, "sessions", "color"):

        cursor.execute("""

            ALTER TABLE sessions

            ADD COLUMN color TEXT DEFAULT '#4285F4'

        """)

    # --------------------------
    # sessions.status
    # --------------------------

    if not column_exists(cursor, "sessions", "status"):

        cursor.execute("""

            ALTER TABLE sessions

            ADD COLUMN status TEXT DEFAULT 'Scheduled'

        """)

    conn.commit()

    conn.close()

    print("Calendar upgrade completed.")