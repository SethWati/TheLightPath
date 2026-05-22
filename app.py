from datetime import date, timedelta
import random
import sqlite3

import joblib
import pandas as pd
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
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


def get_history_window(conn, habit_id, today, days=30):
    """Return the last `days` daily statuses for a habit, oldest first.

    Each entry is {'date': iso, 'status': 1|0|None}. Used to render the per-card
    sparkline so the user can physically see the 30-day trajectory and the
    rightmost three cells — the exact window the Random Forest is reading.
    """
    cutoff = today - timedelta(days=days - 1)
    rows = conn.execute(
        '''SELECT check_in_date, status FROM check_ins
           WHERE habit_id = ? AND check_in_date >= ? AND check_in_date <= ?''',
        (habit_id, cutoff.isoformat(), today.isoformat()),
    ).fetchall()
    by_date = {r['check_in_date']: r['status'] for r in rows}
    return [
        {
            'date': (today - timedelta(days=offset)).isoformat(),
            'status': by_date.get((today - timedelta(days=offset)).isoformat()),
        }
        for offset in range(days - 1, -1, -1)
    ]


def get_today_status(conn, habit_id, today):
    row = conn.execute(
        'SELECT status FROM check_ins WHERE habit_id = ? AND check_in_date = ?',
        (habit_id, today.isoformat()),
    ).fetchone()
    return row['status'] if row else None


def predict_failure(history, category):
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

    # train_model.py uses columns [prev_1, prev_2, prev_3] = [yesterday, 2-ago, 3-ago]
    # followed by one-hot category columns (cat_Health, cat_Learning, cat_Productivity).
    # history is [3-ago, 2-ago, yesterday], so reverse to match training order, then
    # rebuild the full feature row in the exact column order the model was trained on.
    row = {
        'prev_1': int(history[2]),
        'prev_2': int(history[1]),
        'prev_3': int(history[0]),
    }
    for col in model.feature_names_in_:
        if col.startswith('cat_'):
            row[col] = 1 if col == f'cat_{category}' else 0

    features = pd.DataFrame([row], columns=list(model.feature_names_in_))
    probs = model.predict_proba(features)[0]
    failure_idx = list(model.classes_).index(0)
    return float(probs[failure_idx]), False


def allowed_tags_for_religion(religion):
    """Map a user's declared religion to the set of library tags they're shown.

    Always includes 'universal'. Secular content is shown to everyone except
    the most conservative religious selection (we still show it to all here
    because secular wisdom is generally well-received; tune later if needed).
    """
    base = {'universal', 'secular'}
    if not religion or religion in ('Prefer not to say',):
        return base
    if religion == 'Christianity':
        return base | {'christian', 'stoic'}
    if religion == 'Islam':
        return base | {'islamic', 'stoic'}
    if religion == 'Judaism':
        return base | {'jewish', 'stoic'}
    if religion == 'Buddhism':
        return base | {'buddhist', 'eastern', 'stoic'}
    if religion == 'Hinduism':
        return base | {'hindu', 'eastern', 'stoic'}
    if religion == 'Sikhism':
        return base | {'eastern', 'stoic'}
    if religion == 'Spiritual':
        # Open to any spiritual tradition
        return base | {'christian', 'islamic', 'jewish', 'buddhist', 'hindu',
                       'eastern', 'stoic', 'indigenous', 'african'}
    if religion in ('Agnostic', 'Atheist'):
        return base | {'stoic'}
    return base | {'stoic'}


def filter_rows_by_tags(rows, allowed):
    """Keep rows whose tags overlap the allowed set (or whose tags are blank)."""
    out = []
    for r in rows:
        tags = (r['tags'] or '').strip() if 'tags' in r.keys() else ''
        if not tags:
            out.append(r)
            continue
        row_tags = {t.strip() for t in tags.split(',') if t.strip()}
        if row_tags & allowed:
            out.append(r)
    return out


def pick_intervention(conn, category, user_id=None):
    """Pick a library entry for a category, biased to the user's worldview."""
    rows = conn.execute(
        'SELECT type, message, source, tags FROM intervention_library WHERE category = ?',
        (category,),
    ).fetchall()
    if not rows:
        return None
    if user_id is not None:
        prof = get_profile(conn, user_id)
        if prof:
            allowed = allowed_tags_for_religion(prof.get('religion'))
            filtered = filter_rows_by_tags(rows, allowed)
            if filtered:
                rows = filtered
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


def build_habit_view(conn, habit_row, today, log_new_interventions=True):
    """Compute the full dashboard view for a single habit.

    Pulled out of home() so the AJAX endpoints (check_in, add_habit) can return
    exactly the same shape of data the dashboard was first rendered with. This
    keeps the live UI updates consistent with the initial Jinja2 render.
    """
    history = get_recent_history(conn, habit_row['id'], today)
    prob_fail, used_fallback = predict_failure(history, habit_row['category'])
    today_status = get_today_status(conn, habit_row['id'], today)
    current_streak = get_current_streak(conn, habit_row['id'], today)
    at_risk = prob_fail >= RISK_THRESHOLD and today_status != 1
    intervention = (
        pick_intervention(conn, habit_row['category'], user_id=session.get('user_id'))
        if at_risk else None
    )
    if intervention is not None and log_new_interventions:
        log_intervention(conn, habit_row['id'], intervention['message'])
    # Defensive .keys() lookup — habit_row may originate from either the habits
    # table (which has target_*) or a partial SELECT, so we don't assume.
    keys = habit_row.keys()
    return {
        'id': habit_row['id'],
        'name': habit_row['habit_name'],
        'category': habit_row['category'],
        'target_measure': habit_row['target_measure'] if 'target_measure' in keys else None,
        'target_time': habit_row['target_time'] if 'target_time' in keys else None,
        'today_status': today_status,
        'prob_fail': prob_fail,
        'used_fallback': used_fallback,
        'at_risk': at_risk,
        'intervention': dict(intervention) if intervention is not None else None,
        'streak': current_streak,
        'history_30d': get_history_window(conn, habit_row['id'], today),
    }


def wants_json():
    """True when the request wants a JSON response (XHR/fetch) instead of an HTML redirect."""
    accept = request.headers.get('Accept', '')
    return request.is_json or 'application/json' in accept or \
           request.headers.get('X-Requested-With') == 'XMLHttpRequest'


# --- NEW AUTHENTICATION ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Create a new account.

    On success, signs the new user in and sends them to the First Light
    onboarding page so the dashboard's content can be tailored from the start.
    """
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''

        if not username or len(username) < 3:
            flash('Choose a username of at least three characters.')
            return render_template('register.html')
        if len(password) < 6:
            flash('Pick a password of at least six characters — comfort over complexity is fine.')
            return render_template('register.html')
        if password != confirm:
            flash('Those passwords don’t match yet. Try once more.')
            return render_template('register.html')

        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            flash('That username is already on the path. Try another, or sign in.')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash),
        )
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        session['user_id'] = new_id
        session['username'] = username
        return redirect(url_for('onboarding'))

    return render_template('register.html')


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


PROFILE_FIELDS = (
    'ethnicity', 'religion', 'age_band', 'occupation',
    'marital_status', 'hobbies', 'foods', 'enjoys',
)


def get_profile(conn, user_id):
    """Return the user_profile row as a dict, or None if it doesn't exist."""
    row = conn.execute(
        'SELECT * FROM user_profile WHERE user_id = ?', (user_id,)
    ).fetchone()
    return dict(row) if row else None


@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    """First Light — the dawn of TheLightPath.

    Captures the user's profile so the dashboard's "A light for today" panel
    and the in-habit interventions can be filtered to their worldview, life
    stage, and interests. Every field is optional — a user can skip and still
    use the app perfectly well; the engine just falls back to universal
    content where data is missing.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()

    if request.method == 'POST':
        values = {f: (request.form.get(f) or '').strip() or None for f in PROFILE_FIELDS}
        existing = conn.execute(
            'SELECT user_id FROM user_profile WHERE user_id = ?',
            (session['user_id'],),
        ).fetchone()
        if existing:
            set_clause = ', '.join(f"{f} = ?" for f in PROFILE_FIELDS)
            conn.execute(
                f'UPDATE user_profile SET {set_clause} WHERE user_id = ?',
                (*values.values(), session['user_id']),
            )
        else:
            cols = ', '.join(['user_id', *PROFILE_FIELDS])
            qs = ', '.join(['?'] * (1 + len(PROFILE_FIELDS)))
            conn.execute(
                f'INSERT INTO user_profile ({cols}) VALUES ({qs})',
                (session['user_id'], *values.values()),
            )
        conn.commit()
        conn.close()
        flash('Your path is set. Welcome.')
        return redirect(url_for('home'))

    profile = get_profile(conn, session['user_id']) or {}
    conn.close()
    return render_template('onboarding.html', profile=profile)


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

    # First-time visit: nudge brand-new accounts through First Light once.
    # We only redirect when the user has neither a profile nor any habits yet —
    # that way returning users who have skipped onboarding aren't pestered.
    has_profile = conn.execute(
        'SELECT 1 FROM user_profile WHERE user_id = ?', (user_id,)
    ).fetchone()
    has_habits = conn.execute(
        'SELECT 1 FROM habits WHERE user_id = ? LIMIT 1', (user_id,)
    ).fetchone()
    if not has_profile and not has_habits:
        conn.close()
        return redirect(url_for('onboarding'))

    habits = conn.execute(
        '''SELECT id, habit_name, category, target_measure, target_time
           FROM habits WHERE user_id = ? ORDER BY habit_name''',
        (user_id,),
    ).fetchall()

    habit_views = [build_habit_view(conn, h, today) for h in habits]

    conn.close()
    return render_template(
        'index.html',
        user=user,
        habits=habit_views,
        today=today,
        threshold=RISK_THRESHOLD,
    )


def _best_streak_from_history(history_30d):
    """Longest run of consecutive 1s in a 30-day history list."""
    best, run = 0, 0
    for cell in history_30d:
        if cell['status'] == 1:
            run += 1
            if run > best:
                best = run
        else:
            run = 0
    return best


@app.route('/api/habit/<int:habit_id>', methods=['GET'])
def api_habit_detail(habit_id):
    """Extended view of a single habit for the detail modal."""
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorised'}), 401

    conn = get_db()
    habit = conn.execute(
        '''SELECT id, habit_name, category, target_measure, target_time, created_at
           FROM habits WHERE id = ? AND user_id = ?''',
        (habit_id, session['user_id']),
    ).fetchone()
    if habit is None:
        conn.close()
        return jsonify({'error': 'not found'}), 404

    today = date.today()
    view = build_habit_view(conn, habit, today, log_new_interventions=False)
    history = view['history_30d']

    # Recent interventions audit log
    intervention_rows = conn.execute(
        '''SELECT intervention_message, triggered_at FROM interventions
           WHERE habit_id = ? ORDER BY triggered_at DESC LIMIT 10''',
        (habit_id,),
    ).fetchall()
    conn.close()

    completed_30 = sum(1 for c in history if c['status'] == 1)
    missed_30 = sum(1 for c in history if c['status'] == 0)
    best_streak = _best_streak_from_history(history)
    window = history[-3:]  # the three cells the Random Forest reads

    return jsonify({
        'habit': view,
        'created_at': habit['created_at'],
        'stats': {
            'completed_30': completed_30,
            'missed_30': missed_30,
            'best_streak_30': best_streak,
        },
        'model_window': window,
        'recent_interventions': [dict(r) for r in intervention_rows],
    })


CHAT_CATEGORY_HINTS = {
    'Health':        ('gym', 'workout', 'exercise', 'walk', 'run', 'water', 'sleep',
                      'eat', 'diet', 'health', 'tired', 'energy', 'body', 'rest',
                      'meditat', 'breath', 'stress'),
    'Learning':      ('study', 'read', 'book', 'class', 'lecture', 'exam', 'revise',
                      'learn', 'course', 'university', 'school', 'memor', 'practice',
                      'piano', 'language'),
    'Productivity':  ('work', 'job', 'deadline', 'project', 'email', 'tasks', 'todo',
                      'procrastinat', 'focus', 'distract', 'productive', 'plan',
                      'manage', 'time'),
}
CHAT_MOOD_HINTS = {
    'low':       ('tired', 'exhausted', 'drained', 'low', 'sad', 'down', 'stuck',
                  'lonely', 'lost', 'unmotivated', 'can\'t', 'cannot', 'overwhelm'),
    'anxious':   ('anxious', 'anxiety', 'worried', 'stressed', 'panic', 'nervous', 'afraid'),
    'angry':     ('angry', 'frustrated', 'annoyed', 'furious', 'irritated'),
    'positive':  ('happy', 'excited', 'good', 'great', 'amazing', 'proud', 'motivated', 'glad'),
    'confused':  ('confused', 'don\'t know', 'unsure', 'lost', 'not sure'),
}


def detect_chat_intent(message):
    """Very small intent classifier — keyword sniff, no ML.

    Returns (category_or_None, mood_or_None). This matches the report's
    description of Lee et al.'s "semi-generative chatbot": adaptive replies
    along a small number of predefined conversational paths.
    """
    m = (message or '').lower()
    category = None
    for cat, words in CHAT_CATEGORY_HINTS.items():
        if any(w in m for w in words):
            category = cat
            break
    mood = None
    for label, words in CHAT_MOOD_HINTS.items():
        if any(w in m for w in words):
            mood = label
            break
    return category, mood


MOOD_OPENERS = {
    'low':      [
        "I hear you — low days are real. Here’s a gentle thought to sit with:",
        "On heavy days, the bar should drop, not the streak. A small offering:",
        "When the energy isn’t there, kindness is the move. Try this:",
    ],
    'anxious':  [
        "Anxious minds shrink the world. Let’s widen it a little:",
        "When the chest feels tight, a slow exhale and a soft thought help. Try this:",
        "Worry loves an empty space. Give it something steadier to hold:",
    ],
    'angry':    [
        "Frustration is honest signal. Here’s a steadier voice to balance it:",
        "When the temperature rises, an older voice can cool it down:",
    ],
    'positive': [
        "Love that you’re feeling it — let’s feed the fire:",
        "Bright energy is the best moment to act. Use it:",
        "When the wind is at your back, sail. Try this:",
    ],
    'confused': [
        "Not knowing is the start of a real answer. A nudge to think with:",
        "Confusion isn’t failure — it’s your brain about to grow. Sit with this:",
    ],
}
GENERIC_OPENERS = [
    "Here’s a thought for the moment:",
    "Take this with you:",
    "Try this on:",
    "A small light for now:",
]
FOLLOWUPS = [
    "What’s the smallest version of your habit you could do in the next ten minutes?",
    "If you only did this for two minutes today, what would that look like?",
    "Is there one small obstacle we could remove for tomorrow’s attempt?",
    "Which corner of life is this one really about — Health, Learning or Productivity?",
    "Would it help to set a specific time for this habit?",
]


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Lightweight semi-generative advice channel.

    Parses the user's message for a probable habit category and mood, then
    composes a reply: a warm opener (mood-aware) + a relevant library quote
    (worldview-filtered) + a small open question that prompts the user's own
    next step. No external LLM is needed; the report (Lee et al., 2025) calls
    out predefined conversational paths plus generative-style framing, which
    is exactly the shape of this endpoint.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorised'}), 401
    payload = request.get_json(silent=True) or {}
    message = (payload.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'empty message'}), 400
    if len(message) > 800:
        message = message[:800]

    category, mood = detect_chat_intent(message)

    conn = get_db()
    profile = get_profile(conn, session['user_id'])
    allowed_tags = allowed_tags_for_religion(profile.get('religion') if profile else None)

    # Choose a library quote from the inferred category if any; otherwise General.
    target_cat = category if category in ('Health', 'Learning', 'Productivity') else 'General'
    candidates = conn.execute(
        'SELECT category, type, message, source, tags FROM intervention_library WHERE category = ?',
        (target_cat,),
    ).fetchall()
    if not candidates and target_cat != 'General':
        candidates = conn.execute(
            'SELECT category, type, message, source, tags FROM intervention_library WHERE category = ?',
            ('General',),
        ).fetchall()
    conn.close()

    filtered = filter_rows_by_tags(candidates, allowed_tags) or candidates
    quote = random.choice(filtered) if filtered else None

    opener = random.choice(MOOD_OPENERS.get(mood, GENERIC_OPENERS))
    followup = random.choice(FOLLOWUPS)

    reply_parts = [opener]
    if quote is not None:
        attribution = f" — {quote['source']}" if quote['source'] else ""
        reply_parts.append(f"“{quote['message']}”{attribution}")
    reply_parts.append(followup)

    return jsonify({
        'reply': '\n\n'.join(reply_parts),
        'detected': {'category': category, 'mood': mood},
    })


@app.route('/api/insight', methods=['GET'])
def api_insight():
    """Return a random entry from intervention_library.

    Powers the always-visible "A light for today" panel so users see a piece
    of encouragement, health fact, scripture or philosophy every visit, not
    only when a habit is at risk.

    Smart category bias: if the user has habits, the pool is restricted to
    those categories plus 'General' — so the insight is relevant to the life
    they're actually tracking. If they have no habits yet, it falls back to
    'General' alone (universal encouragement).

    Optional ?exclude=<id> avoids re-showing the previous insight so repeated
    clicks of the refresh button actually cycle.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorised'}), 401

    exclude = request.args.get('exclude')
    conn = get_db()

    user_cats = [r['category'] for r in conn.execute(
        'SELECT DISTINCT category FROM habits WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()]
    allowed_cats = sorted(set(user_cats) | {'General'}) if user_cats else ['General']
    placeholders = ','.join('?' * len(allowed_cats))

    params = list(allowed_cats)
    where_extra = ''
    if exclude and exclude.isdigit():
        where_extra = ' AND id != ?'
        params.append(int(exclude))

    # Pull a wider candidate pool, then filter in Python by worldview tags.
    # Random sampling on the filtered set in Python is fine for a library of
    # this size (~100 entries) and keeps the SQL portable.
    candidates = conn.execute(
        f'''SELECT id, category, type, message, source, tags
            FROM intervention_library
            WHERE category IN ({placeholders}){where_extra}''',
        params,
    ).fetchall()
    profile = get_profile(conn, session['user_id'])
    conn.close()

    allowed_tags = allowed_tags_for_religion(profile.get('religion') if profile else None)
    filtered = filter_rows_by_tags(candidates, allowed_tags)
    if not filtered:
        filtered = candidates  # fail-open
    if not filtered:
        return jsonify({'insight': None})

    row = random.choice(filtered)
    chosen = {k: row[k] for k in row.keys() if k != 'tags'}
    return jsonify({'insight': chosen})


@app.route('/check_in/<int:habit_id>', methods=['POST'])
def check_in(habit_id):
    """Marks a habit as complete for today.

    Returns JSON with the refreshed habit view when called from the AJAX layer,
    otherwise falls back to a classic redirect so the page still works without
    JavaScript.
    """
    if 'user_id' not in session:
        if wants_json():
            return jsonify({'error': 'unauthorised'}), 401
        return redirect(url_for('login'))

    today = date.today()
    today_iso = today.isoformat()
    conn = get_db()

    # SECURITY: verify the habit actually belongs to the logged-in user before
    # touching its check-ins. Without this, an attacker could check in habits
    # they don't own simply by guessing IDs.
    habit = conn.execute(
        '''SELECT id, habit_name, category, target_measure, target_time
           FROM habits WHERE id = ? AND user_id = ?''',
        (habit_id, session['user_id']),
    ).fetchone()
    if habit is None:
        conn.close()
        if wants_json():
            return jsonify({'error': 'not found'}), 404
        return redirect(url_for('home'))

    existing = conn.execute(
        'SELECT id FROM check_ins WHERE habit_id = ? AND check_in_date = ?',
        (habit_id, today_iso),
    ).fetchone()
    if existing:
        conn.execute('UPDATE check_ins SET status = 1 WHERE id = ?', (existing['id'],))
    else:
        conn.execute(
            'INSERT INTO check_ins (habit_id, check_in_date, status) VALUES (?, ?, 1)',
            (habit_id, today_iso),
        )
    conn.commit()

    if wants_json():
        # log_new_interventions=False because the habit is now Completed, so
        # build_habit_view will not produce an intervention anyway. Setting it
        # explicitly documents the intent and avoids a spurious audit-log row.
        view = build_habit_view(conn, habit, today, log_new_interventions=False)
        conn.close()
        return jsonify({'habit': view, 'threshold': RISK_THRESHOLD})

    conn.close()
    return redirect(url_for('home'))


@app.route('/add_habit', methods=['POST'])
def add_habit():
    """Securely adds a new custom habit for the logged-in user."""
    if 'user_id' not in session:
        if wants_json():
            return jsonify({'error': 'unauthorised'}), 401
        return redirect(url_for('login'))

    habit_name = (request.form.get('habit_name') or '').strip()
    category = request.form.get('category')
    target_measure = (request.form.get('target_measure') or '').strip() or None
    target_time = (request.form.get('target_time') or '').strip() or None
    user_id = session['user_id']

    if not habit_name or category not in ('Health', 'Learning', 'Productivity'):
        if wants_json():
            return jsonify({'error': 'invalid input'}), 400
        return redirect(url_for('home'))

    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO habits (user_id, habit_name, category, target_measure, target_time)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, habit_name, category, target_measure, target_time),
    )
    new_id = cursor.lastrowid
    conn.commit()

    if wants_json():
        habit_row = conn.execute(
            '''SELECT id, habit_name, category, target_measure, target_time
               FROM habits WHERE id = ?''', (new_id,)
        ).fetchone()
        view = build_habit_view(conn, habit_row, date.today())
        conn.close()
        return jsonify({'habit': view, 'threshold': RISK_THRESHOLD})

    conn.close()
    return redirect(url_for('home'))


@app.route('/delete_habit/<int:habit_id>', methods=['POST'])
def delete_habit(habit_id):
    """Securely deletes a habit and all associated relational data."""
    if 'user_id' not in session:
        if wants_json():
            return jsonify({'error': 'unauthorised'}), 401
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
        if not wants_json():
            flash('Target successfully deleted.')

    conn.close()
    if wants_json():
        return jsonify({'deleted_id': habit_id})
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)