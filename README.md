# TheLightPath

> A proactive habit tracker that predicts failure before it happens and intervenes with curated, context-specific support.

---

## About this README

**This README was added to the repository on 28 May 2026, after the project's formal submission deadline of 22 May 2026.** It is not part of the assessed submission. The Turnitin report, the code submitted to my supervisor, and the inital things are all unchanged from what was submitted on the deadline.

The purpose of this file is repository documentation for anyone visiting the public GitHub page (it is for future readers). It describes the project that was submitted, but the file itself was not part of that submission and I am not claiming it to be a part at all.

---

## Project context

This was my final-year undergraduate project for **CTEC3451 Development Project** at De Montfort University, BSc Computer Science.

- **Author:** Seth Gondwe (P2834987)
- **Supervisor:** Dr Mohsen Zahedi
- **Module Leader:** Dr Hossein Malekmohamadi
- **Submission date:** 22 May 2026
- **Viva:** 28 May 2026

---

## What it does

Most habit-tracking apps log what has already happened. TheLightPath does something different. It uses a Random Forest classifier trained on a rolling three-day check-in history to predict the probability of a user missing today's habit, and when that probability crosses a calibrated threshold, it surfaces a category-matched intervention drawn from a curated library of physiological facts, actionable advice, and scriptural encouragement.

The thesis is that retrospective tracking fails the user at the moment they actually need help. Catching the start of a downward trend, and acting on it, is the difference between a tool that records failure and a tool that prevents it.

---

## Architecture

Three-layer Model-View-Controller pipeline:

| Layer | Implementation | Role |
|-------|---------------|------|
| Data | SQLite (5 normalised tables, foreign keys with `ON DELETE CASCADE`, CHECK and UNIQUE constraints) | Stores users, habits, daily check-ins, intervention audit log, and the reusable intervention library |
| Logic | scikit-learn `RandomForestClassifier` (100 trees, three lagged features) with rule-based fallback | Predicts probability of failure for today, given the last three days |
| Presentation | Flask + Jinja2 + Bootstrap 5 + Chart.js | Renders the dashboard, surfaces model confidence transparently to the user |

---

## Setup

Requires Python 3.10+.

```bash
# Install dependencies
pip install flask pandas scikit-learn joblib werkzeug

# Build the database from the canonical schema
python database_setup.py

# Load the intervention library
python seed_interventions.py

# Generate synthetic training data (5 users, 30-day trajectories)
python generate_data.py

# Train the Random Forest model
python train_model.py

# Register a real user (asks for username and password at the prompt)
python register_user.py

# Start the application
python app.py
```

Then open `http://127.0.0.1:5000/login` in a browser.

---

## Key design decisions

**Risk threshold at 0.4, not 0.5.** Below the conventional default because the cost of missing a struggling user (false negative) is asymmetrically worse than the cost of an unnecessary intervention (false positive). This is standard cost-sensitive threshold tuning, drawn from the Just-in-Time Adaptive Intervention literature (Nahum-Shani et al., 2018).

**Three-day rolling window.** Short enough to detect drift early but long enough to give the model meaningful signal. Inspecting `feature_importances_` on the trained model shows the OLDEST day of the window (`prev_3` = 0.388) carries the most weight, which aligns with stress-context vulnerability models that argue risk accumulates before it surfaces as observable failure.

**Rule-based fallback when history is incomplete.** Implements the risk mitigation specified in the project contract. The fallback is also surfaced to the user via a visible `used_fallback` indicator on the dashboard, so the system never hides reduced confidence behind a confident-looking number.

**Separation of intervention catalogue from intervention audit log.** Two tables, not one. The library is content; the audit log is event history. This is third normal form database design and lets the same message be reused across many triggering events without duplication.

---

## Repository structure

```
TheLightPath/
├── app.py                    Flask routes, prediction pipeline, MVC controller
├── database_setup.py         Canonical SQLite schema; run once to initialise
├── seed_interventions.py     Loads the 9-entry intervention library
├── generate_data.py          Synthetic data generator (5 users x 30 days)
├── train_model.py            Random Forest training, evaluation, pkl serialisation
├── register_user.py          Admin script to create a real user with hashed password
├── reset_password.py         Admin script to reset a user's password
├── templates/
│   ├── login.html            Login page
│   └── index.html            Main dashboard with risk chart and habit cards
├── lightpath.db              SQLite database (regenerate with database_setup.py)
└── lightpath_ai_model.pkl    Trained Random Forest (regenerate with train_model.py)
```

---

## Known limitations

This is a Minimum Viable Product so things are deliberately out of scope
- **No CSRF protection on forms.** The next enhancement would integrate Flask-WTF. In the current local-demo deployment the attack surface is minimal; in any wider deployment this would need to be addressed.
- **Flask secret key is hardcoded in `app.py`.** It should be loaded from an environment variable. The fix is a few lines.
- **Trained on synthetic data.** The pipeline and the model is real, but the data is fake and generated. Validating the model on real user behaviour under proper ethics approval is the obvious natural next step.

---

## License

Academic submission. All rights reserved by the author.
