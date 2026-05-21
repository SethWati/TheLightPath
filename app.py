from datetime import date, timedelta
import random
import sqlite3

import joblib
import pandas as pd
from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'lightpath.db'
MODEL_PATH = 'lightpath_ai_model.pkl'

# P(failure) at or above this triggers an intervention. 0.4 (rather than 0.5) errs on
# the side of intervening, which matches the project's proactive-support thesis.
RISK_THRESHOLD = 0.4

app = Flask(__name__)
# Secret key is required for Flask sessions to work securely
app.secret_key = 'super_secret_lightpath_key_for_development' 

model = joblib.load(MODEL_PATH)


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def get_recent_history(conn, habit_id, today, days=3):
    """Return [3-days-ago, 2-days-ago, yesterday] statuses (1/0/None for missing)."""
    cutoff = today - timedelta(days=days)
    rows = conn.execute(
        '''SELECT check_in_date, status FROM check_ins
           WHERE habit_id = ? AND check_in_date >= ? AND check_in_date < ?''',
        (habit_id, cutoff.isoformat(), today.isoformat()),
    ).fetchall()
    by_date = {r['check_in_date']: r['status'] for r in rows}
    return [by_date.get((today - timedelta(days=offset)).isoformat())
            for offset in range(days, 0, -1)]


def get_today_status(conn, habit_id, today):
    row = conn.execute(
        'SELECT status FROM check_ins WHERE habit_id = ? AND check_in_date = ?',
        (habit_id, today.isoformat()),
    ).fetchone()
    return row['status'] if row else None


def predict_failure(history):
    """Return (prob_failure, used_fallback).

    Falls back to a simple rule when the 3-day window has gaps, satisfying the
    risk mitigation in the project contract: "if the ML model struggles, use
    simpler rules as a fallback to trigger the UI interventions."
    """
    if any(h is None for h in history):
        known = [h for h in history if h is not None]
        if known and known.count(0) / len(known) >= 0.5:
            return 0.7, True
        return 0.2, True

    # train_model.py uses columns [prev_1, prev_2, prev_3] = [yesterday, 2-ago, 3-ago].
    # history is [3-ago, 2-ago, yesterday], so reverse to match training order.
    features = pd.DataFrame(
        [[history[2], history[1], history[0]]],
        columns=['prev_1', 'prev_2', 'prev_3'],
    )
    probs = model.predict_proba(features)[0]
    failure_idx = list(model.classes_).index(0)
    return float(probs[failure_idx]), False


def pick_intervention(conn, category):
    rows = conn.execute(
        'SELECT type, message, source FROM intervention_library WHERE category = ?',
        (category,),
    ).fetchall()
    return random.choice(rows) if rows else None


def log_intervention(conn, habit_id, message):
    conn.execute(
        'INSERT INTO interventions (habit_id, intervention_message) VALUES (?, ?)',
        (habit_id, message),
    )
    conn.commit()


def get_current_streak(conn, habit_id, today):
    """Calculates the current streak of consecutive completed days."""
    # Retrieve all dates where the habit was successfully completed
    rows = conn.execute(
        'SELECT check_in_date FROM check_ins WHERE habit_id = ? AND status = 1',
        (habit_id,)
    ).fetchall()
    
    completed_dates = {row['check_in_date'] for row in rows}
    streak = 0
    
    # If today is completed, start the streak at 1 and look at yesterday
    if today.isoformat() in completed_dates:
        streak += 1
        check_date = today - timedelta(days=1)
    else:
        # If today is not completed, the streak is still kept alive by yesterday
        check_date = today - timedelta(days=1)
        
    # Walk backwards day by day until a gap is found
    while check_date.isoformat() in completed_dates:
        streak += 1
        check_date -= timedelta(days=1)
        
    return streak


# --- NEW AUTHENTICATION ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        # Temporary fallback for the synthetic MVP users who don't have hashed passwords yet
        if user:
            if check_password_hash(user['password_hash'], password) or user['password_hash'] == 'hashed_password_123':
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('home'))
        
        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- PROTECTED HOME ROUTE ---

@app.route('/')
def home():
    # Kick the user back to the login page if they don't have an active session
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = date.today()
    conn = get_db()

    # Fetch the actual logged-in user from the session dynamically
    user_id = session['user_id']
    user = conn.execute(
        'SELECT id, username FROM users WHERE id = ?', (user_id,)
    ).fetchone()

    habits = conn.execute(
        'SELECT id, habit_name, category FROM habits WHERE user_id = ? ORDER BY habit_name',
        (user_id,),
    ).fetchall()

    habit_views = []
    for h in habits:
        history = get_recent_history(conn, h['id'], today)
        prob_fail, used_fallback = predict_failure(history)
        today_status = get_today_status(conn, h['id'], today)
        
        current_streak = get_current_streak(conn, h['id'], today)

        at_risk = prob_fail >= RISK_THRESHOLD and today_status != 1
        intervention = pick_intervention(conn, h['category']) if at_risk else None
        
        if intervention is not None:
            log_intervention(conn, h['id'], intervention['message'])
            
        habit_views.append({
            'id': h['id'],
            'name': h['habit_name'],
            'category': h['category'],
            'today_status': today_status,
            'prob_fail': prob_fail,
            'used_fallback': used_fallback,
            'at_risk': at_risk,
            'intervention': intervention,
            'streak': current_streak,
        })

    conn.close()
    return render_template(
        'index.html',
        user=user,
        habits=habit_views,
        today=today,
        threshold=RISK_THRESHOLD,
    )


@app.route('/check_in/<int:habit_id>', methods=['POST'])
def check_in(habit_id):
    """Handles the user marking a habit as complete for today."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    today = date.today().isoformat()
    
    existing = conn.execute(
        'SELECT id FROM check_ins WHERE habit_id = ? AND check_in_date = ?',
        (habit_id, today)
    ).fetchone()
    
    if existing:
        conn.execute(
            'UPDATE check_ins SET status = 1 WHERE id = ?',
            (existing['id'],)
        )
    else:
        conn.execute(
            'INSERT INTO check_ins (habit_id, check_in_date, status) VALUES (?, ?, 1)',
            (habit_id, today)
        )
        
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))


@app.route('/add_habit', methods=['POST'])
def add_habit():
    """Securely adds a new custom habit for the logged-in user."""
    # Ensure only authenticated users can add habits
    if 'user_id' not in session:
        return redirect(url_for('login'))

    habit_name = request.form.get('habit_name')
    category = request.form.get('category')
    user_id = session['user_id']

    # Basic validation to ensure empty forms are not submitted
    if habit_name and category:
        conn = get_db()
        conn.execute(
            'INSERT INTO habits (user_id, habit_name, category) VALUES (?, ?, ?)',
            (user_id, habit_name.strip(), category)
        )
        conn.commit()
        conn.close()

    # Refresh the dashboard to instantly display the new habit
    return redirect(url_for('home'))


@app.route('/delete_habit/<int:habit_id>', methods=['POST'])
def delete_habit(habit_id):
    """Securely deletes a habit and all associated relational data."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    
    # SECURITY: Verify the habit actually belongs to the logged-in user
    habit = conn.execute(
        'SELECT id FROM habits WHERE id = ? AND user_id = ?', 
        (habit_id, user_id)
    ).fetchone()
    
    if habit:
        # Step 1: Delete all child records to satisfy FOREIGN KEY constraints
        conn.execute('DELETE FROM check_ins WHERE habit_id = ?', (habit_id,))
        conn.execute('DELETE FROM interventions WHERE habit_id = ?', (habit_id,))
        
        # Step 2: Safely delete the parent habit now that it has no dependents
        conn.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
        
        conn.commit()
        flash('Target successfully deleted.')
        
    conn.close()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)