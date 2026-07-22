import sqlite3
from config import DATABASE_NAME


def run_migrations(cursor):
    """Ensure existing databases receive missing columns without wiping data."""
    # Check if 'curriculum_track' exists in 'students'
    cursor.execute("PRAGMA table_info(students);")
    columns = [col[1] for col in cursor.fetchall()]

    if columns and "curriculum_track" not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN curriculum_track TEXT DEFAULT '1st Grade General Math';")
        print("Migrated: Added 'curriculum_track' column to 'students' table.")

    # Check if 'zoom_link' exists in 'sessions'
    cursor.execute("PRAGMA table_info(sessions);")
    session_columns = [col[1] for col in cursor.fetchall()]

    if session_columns and "zoom_link" not in session_columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN zoom_link TEXT;")
        print("Migrated: Added 'zoom_link' column to 'sessions' table.")


def initialize_database():
    conn = sqlite3.connect(DATABASE_NAME)

    with conn:
        cursor = conn.cursor()

        # Enable Foreign Keys
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Students table (Parent table)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            grade TEXT,
            subject TEXT,
            curriculum_track TEXT DEFAULT '1st Grade General Math',
            email TEXT,
            phone TEXT,
            zoom_link TEXT,
            meeting_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        );
        """)

        # 2. Users table (Child of Students)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            student_id INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
        );
        """)

        # 3. Payments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            period TEXT,
            notes TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        # 4. Homework table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            uploaded_by TEXT NOT NULL,
            file_path TEXT,
            file_link TEXT,
            comment TEXT,
            teacher_feedback TEXT,
            status TEXT DEFAULT 'Assigned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        # 5. Sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
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
            zoom_link TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        # 6. Attendance table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            session_date DATE NOT NULL,
            session_time TEXT NOT NULL,
            status TEXT DEFAULT 'Present',
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, session_date, session_time),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        # 7. Curriculum Resources Vault table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade_track TEXT NOT NULL,
            resource_title TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            direct_url TEXT,
            file_path TEXT,
            teacher_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 8. Reports table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date DATE,
            end_date DATE,
            generated_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Safely run schema updates for existing database files
        run_migrations(cursor)

        # Default admin seed account
        cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'admin');
        """)

    conn.close()
    print("Database schema initialized and verified successfully.")


if __name__ == "__main__":
    initialize_database()
