import sqlite3
import sys
import os


# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


from config import DATABASE_NAME


def table_exists(cursor, table_name):

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,)
    )

    return cursor.fetchone() is not None



def migrate():

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()


    if not table_exists(cursor, "curriculum_resources"):

        cursor.execute(
            """
            CREATE TABLE curriculum_resources(

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                grade_track TEXT NOT NULL,

                resource_title TEXT NOT NULL,

                resource_type TEXT,

                direct_url TEXT,

                file_bytes BLOB,

                file_name TEXT,

                teacher_comment TEXT,

                created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

            );
            """
        )


    conn.commit()

    conn.close()


    print("Curriculum Resources table created.")



if __name__ == "__main__":
    migrate()