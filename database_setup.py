import sqlite3

def create_database():
    print("Initialising TheLightPath Database...")

    conn = sqlite3.connect('lightpath.db')
    # ON DELETE CASCADE only takes effect when foreign keys are enabled per connection.
    conn.execute('PRAGMA foreign_keys = ON')
    cursor = conn.cursor()

    # Table 1: Users (Stores login info)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Table 2: Habits — CASCADE so deleting a user removes their habits (no orphan data).
    # target_measure + target_time operationalise SMART goals: every habit has a
    # specific, measurable check-in metric and an explicit time window
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        habit_name TEXT NOT NULL,
        category TEXT NOT NULL,
        target_measure TEXT,
        target_time TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # In-place migration: add the SMART columns to any existing legacy table
    # that pre-dates this schema. Nullable on purpose so old rows remain valid.
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(habits)")}
    if 'target_measure' not in existing_cols:
        cursor.execute("ALTER TABLE habits ADD COLUMN target_measure TEXT")
    if 'target_time' not in existing_cols:
        cursor.execute("ALTER TABLE habits ADD COLUMN target_time TEXT")

    # Table 3: Check-Ins — CASCADE so deleting a habit removes its history.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS check_ins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        check_in_date DATE NOT NULL,
        status INTEGER NOT NULL CHECK (status IN (0, 1)),
        UNIQUE (habit_id, check_in_date),
        FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
    )
    ''')

    # Table 4: Interventions — audit log of when an intervention was triggered for a habit.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        intervention_message TEXT NOT NULL,
        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
    )
    ''')

    # Table 5: Intervention Library — catalog of messages to choose from, keyed by category.
    # Separating the catalog from the audit log keeps the schema normalised and allows the
    # same message to be reused across habits/users without duplication.
    # `tags` (comma-separated) lets the insight engine filter by worldview —
    # e.g. "christian", "secular,stoic", "universal" — so an atheist user
    # never sees a scripture quote and a Buddhist user can be offered Buddhist
    # wisdom.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS intervention_library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        source TEXT,
        tags TEXT
    )
    ''')
    existing_lib_cols = {row[1] for row in cursor.execute("PRAGMA table_info(intervention_library)")}
    if 'tags' not in existing_lib_cols:
        cursor.execute("ALTER TABLE intervention_library ADD COLUMN tags TEXT")

    # Table 6: User Profile — captured by the "First Light" onboarding page.
    # All fields nullable so the user can skip; the insight engine treats an
    # absent value as "no preference" and falls back to universal content.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profile (
        user_id INTEGER PRIMARY KEY,
        ethnicity TEXT,
        religion TEXT,
        age_band TEXT,
        occupation TEXT,
        marital_status TEXT,
        hobbies TEXT,
        foods TEXT,
        enjoys TEXT,
        onboarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()
    print("Success! Database 'lightpath.db' and all tables created.")

if __name__ == '__main__':
    create_database()
