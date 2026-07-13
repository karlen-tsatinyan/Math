import sqlite3
from config import DATABASE_NAME


def initialize_database():

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    PRAGMA foreign_keys = ON;
    """)


    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        role TEXT NOT NULL,

        student_id INTEGER,

        FOREIGN KEY(student_id)
        REFERENCES students(id)

    );
    """)


    # Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_code TEXT UNIQUE NOT NULL,

        first_name TEXT NOT NULL,

        last_name TEXT NOT NULL,

        grade TEXT,

        subject TEXT,

        email TEXT,

        phone TEXT,

        zoom_link TEXT,

        meeting_id TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        active INTEGER DEFAULT 1

    );
    """)


    # Payments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER NOT NULL,

        amount REAL NOT NULL,

        payment_date DATE NOT NULL,

        period TEXT,

        notes TEXT,

        FOREIGN KEY(student_id)
        REFERENCES students(id)

    );
    """)


    # Homework table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS homework(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER NOT NULL,

        uploaded_by TEXT NOT NULL,

        file_path TEXT,

        file_link TEXT,

        comment TEXT,

        teacher_feedback TEXT,

        status TEXT DEFAULT 'Assigned',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(student_id)
        REFERENCES students(id)

    );
    """)


    # Schedule table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER NOT NULL,

        session_date DATE NOT NULL,

        session_time TEXT NOT NULL,

        duration INTEGER DEFAULT 60,

        repeat_type TEXT DEFAULT 'None',

        repeat_until DATE,

        recurring_group TEXT,

        color TEXT DEFAULT '#4285F4',

        topic TEXT,

        notes TEXT,

        status TEXT DEFAULT 'Scheduled',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(student_id)
        REFERENCES students(id)

    );
    """)


    # Attendance table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id INTEGER NOT NULL,

        session_date DATE NOT NULL,

        session_time TEXT NOT NULL,

        status TEXT DEFAULT 'Present',

        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(
            student_id,
            session_date,
            session_time
        ),

        FOREIGN KEY(student_id)
        REFERENCES students(id)

    );
    """)


    # Reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        start_date DATE,

        end_date DATE,

        generated_by TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """)


    # Default admin account
    cursor.execute("""
    INSERT OR IGNORE INTO users
    (
        username,
        password,
        role
    )
    VALUES
    (
        'admin',
        'admin123',
        'admin'
    );
    """)


    conn.commit()

    conn.close()


    print(
        "Database initialized successfully."
    )



if __name__ == "__main__":


    initialize_database()
    