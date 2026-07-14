import sqlite3

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

    if not table_exists(cursor, "homework_grades"):

        cursor.execute(
            """
            CREATE TABLE homework_grades(

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                homework_id INTEGER,

                student_id INTEGER NOT NULL,

                lesson_date DATE,

                topic TEXT,

                score REAL,

                max_score REAL,

                percent REAL,

                grade_letter TEXT,

                teacher_comment TEXT,

                created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(student_id)
                REFERENCES students(id),

                FOREIGN KEY(homework_id)
                REFERENCES homework(id)

            );
            """
        )

    conn.commit()

    conn.close()

    print("Homework Grades table created.")