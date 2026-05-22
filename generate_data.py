"""
generate_data.py — make-believe users and 30 days of pretend check-ins
======================================================================

Synthetic data, on purpose. The report explains why: real human habit data
is heavily imbalanced (most days are successes), and waiting on ethics
approval to collect real data would have killed an 8-week project. So this
script builds a perfectly balanced laboratory dataset where roughly half
the simulated users are on a "success trajectory" (85% completion) and
half are on a "failing trajectory" (start strong, gradually decline).

Run with:   python generate_data.py

It wipes existing check_ins / habits / users first so we always start from
a clean slate. Then we re-train the model on top of this fresh data.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

# Anchor the DB path to this file's folder — see database_setup.py for the
# story behind why this matters.
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lightpath.db')

def generate_synthetic_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("1. Clearing old data to start fresh...")
    cursor.execute('DELETE FROM check_ins')
    cursor.execute('DELETE FROM habits')
    cursor.execute('DELETE FROM users')

    print("2. Generating synthetic users...")
    users = ['Davonte', 'Sarah', 'Shanice', 'Kalisha', 'James']
    for user in users:
        # Simple fake password hash for the MVP
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (user, 'hashed_password_123'))
    
    # Get the inserted user IDs
    cursor.execute('SELECT id, username FROM users')
    user_records = cursor.fetchall()

    print("3. Generating habits and 30 days of check-in data...")
    habit_categories = ['Learning', 'Health', 'Productivity']
    habit_names = ['Piano Practice', 'Drink 2L Water', 'Read 1 Chapter', 'Daily Walk']

    start_date = datetime.now() - timedelta(days=30)

    for user_id, username in user_records:
        # Give each user 2 random habits
        for _ in range(2):
            habit_name = random.choice(habit_names)
            category = random.choice(habit_categories)
            
            cursor.execute('INSERT INTO habits (user_id, habit_name, category) VALUES (?, ?, ?)', 
                           (user_id, habit_name, category))
            habit_id = cursor.lastrowid

            # Determine if this habit is a "Success Trajectory" or "Failing Trajectory"
            # This is CRUCIAL for your machine learning model to learn from!
            is_failing_trajectory = random.choice([True, False])

            # Generate 30 days of check-ins
            for day in range(30):
                current_date = start_date + timedelta(days=day)
                
                if is_failing_trajectory:
                    # If failing, they do well at the start, but success drops off over time
                    success_chance = max(0.1, 0.9 - (day * 0.03)) 
                else:
                    # If succeeding, they are consistent (around 85% success rate)
                    success_chance = 0.85 

                # 1 = success, 0 = missed habit
                status = 1 if random.random() < success_chance else 0

                cursor.execute('INSERT INTO check_ins (habit_id, check_in_date, status) VALUES (?, ?, ?)',
                               (habit_id, current_date.strftime('%Y-%m-%d'), status))

    conn.commit()
    conn.close()
    print("Success! Synthetic data generation complete. Your database is ready for the AI.")

if __name__ == '__main__':
    generate_synthetic_data()