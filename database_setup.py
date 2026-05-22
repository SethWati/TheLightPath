"""
database_setup.py — the schema, lives in one place
==================================================

Run this once (or any time the schema changes) and it'll create every table
TheLightPath needs in the lightpath.db file. It uses CREATE TABLE IF NOT
EXISTS so it's safe to re-run — existing data stays put.

The six tables are:
    users               — login info (hashed password)
    user_profile        — what we learn at "First Light" onboarding
    habits              — the user's actual targets, with category + SMART
                          fields (measurable target + time)
    check_ins           — one row per habit per day, status 0 or 1
    interventions       — the AUDIT LOG of nudges actually delivered
    intervention_library— the static CATALOGUE of nudges we can choose from

Two tables for interventions is on purpose. The library is the dictionary,
the interventions table is the diary — keeps the schema normalised and
stops us from copy-pasting the same quote into hundreds of audit rows.
"""

import sqlite3

def create_database():
    print("Initialising TheLightPath Database...")

    conn = sqlite3.connect('lightpath.db')
    # CASCADE deletes only fire when foreign keys are switched on per connection.
    # SQLite leaves it off by default — must remember to turn it on every time.
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
