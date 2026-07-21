from database import execute


def create_progress_notes_table():
    """Creates the progress_notes table for PostgreSQL/SQLite."""
    try:
        execute(
            """
            CREATE TABLE IF NOT EXISTS progress_notes (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                lesson_date DATE,
                topic TEXT,
                strengths TEXT,
                improvements TEXT,
                homework TEXT,
                next_steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        print("✅ Progress notes table created successfully.")
    except Exception as e:
        print(f"❌ Error creating progress notes table: {e}")


if __name__ == "__main__":
    create_progress_notes_table()
