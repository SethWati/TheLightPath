"""
register_user.py — quick admin tool to add a user from the terminal
==================================================================

For when I'm testing and want a brand new account without going through the
web form. Run it, type a username and password, and a new row drops into
the users table with a properly hashed password. As a bonus, it also gives
the new account one default habit so the dashboard isn't completely empty
on first login.

Run with:   python register_user.py

The web /register route does the same job for end users — this is just the
back-door for me as the developer.
"""

import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = 'lightpath.db'

def create_secure_user():
    print("=== TheLightPath: Secure User Registration ===")
    username = input("Enter a new username: ").strip()
    password = input("Enter a secure password: ").strip()

    if not username or not password:
        print("Error: Username and password cannot be empty.")
        return

    # Hash the password using pbkdf2:sha256 (industry standard)
    hashed_pw = generate_password_hash(password)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Insert the new user into the database
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)', 
            (username, hashed_pw)
        )
        conn.commit()
        user_id = cursor.lastrowid
        print(f"\nSuccess! User '{username}' has been securely registered with ID {user_id}.")
        print("You can now log in to the dashboard.")
        
        # Optional: Give the new user a default habit so the dashboard isn't empty
        cursor.execute(
            "INSERT INTO habits (user_id, habit_name, category) VALUES (?, 'Drink 2L Water', 'Health')",
            (user_id,)
        )
        conn.commit()
        print("A default habit ('Drink 2L Water') has been added to the new account.")
        
    except sqlite3.IntegrityError:
        print(f"\nError: The username '{username}' is already taken. Please try another.")
    finally:
        conn.close()

if __name__ == '__main__':
    create_secure_user()