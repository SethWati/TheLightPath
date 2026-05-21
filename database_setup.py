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
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        habit_name TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

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
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS intervention_library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('health_fact', 'spiritual', 'practical')),
        message TEXT NOT NULL,
        source TEXT
    )
    ''')

    conn.commit()
    conn.close()
    print("Success! Database 'lightpath.db' and all tables created.")

if __name__ == '__main__':
    create_database()
