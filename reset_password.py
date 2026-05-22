"""
reset_password.py — admin-only password reset
=============================================

If a test user forgets their password (or I do), this is the lifeboat. Type
the username, type a new password, and it overwrites the password_hash in
the database with a fresh secure hash. Doesn't expose the old password —
hashes are one-way by design.

Run with:   python reset_password.py

In a real production app this would happen through an email-link flow with
a single-use token, but for a prototype the terminal tool is the right
level of complexity.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

# Anchor to the script folder — same reason as every other script in here.
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lightpath.db')

def reset_password():
    print("=== TheLightPath: Admin Password Reset ===")
    username = input("Enter the username of the locked account: ").strip()
    new_password = input("Enter the new password: ").strip()

    if not username or not new_password:
        print("Error: Username and password cannot be empty.")
        return

    # Generate a new secure hash
    hashed_pw = generate_password_hash(new_password)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Verify the user actually exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()

    if user:
        # Update the hash in the database
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE username = ?',
            (hashed_pw, username)
        )
        conn.commit()
        print(f"\nSuccess! The password for '{username}' has been securely reset.")
    else:
        print(f"\nError: The user '{username}' does not exist in the database.")
        print("Hint: You can run 'python register_user.py' to create a new account.")

    conn.close()

if __name__ == '__main__':
    reset_password()