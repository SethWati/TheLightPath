import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

CATEGORIES = ['Health', 'Learning', 'Productivity']


def train_lightpath_ai():
    print("1. Connecting to the database...")
    conn = sqlite3.connect('lightpath.db')

    # JOIN check_ins with habits so the algorithm can also see WHICH category
    # the habit belongs to (Health / Learning / Productivity). 
    query = """
    SELECT c.habit_id, c.check_in_date, c.status, h.category
    FROM check_ins AS c
    JOIN habits   AS h ON h.id = c.habit_id
    ORDER BY c.habit_id, c.check_in_date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    print("2. Preparing the data for Machine Learning...")
    # We want the AI to look at the last 3 days to predict today.
    # We create columns for "Yesterday", "2 Days Ago", and "3 Days Ago"
    df['prev_1'] = df.groupby('habit_id')['status'].shift(1)
    df['prev_2'] = df.groupby('habit_id')['status'].shift(2)
    df['prev_3'] = df.groupby('habit_id')['status'].shift(3)

    # Drop the first 3 days for each habit since they don't have enough history to make a prediction
    df = df.dropna()

    # One-hot encode the category. Forcing a fixed CATEGORIES order guarantees
    # the columns are identical at train-time and at predict-time even if a
    # category happens to be missing from the live data.
    df['category'] = pd.Categorical(df['category'], categories=CATEGORIES)
    category_dummies = pd.get_dummies(df['category'], prefix='cat').astype(int)

    # Features (X): 3-day window + category dummies. Target (y): today's outcome.
    prev_cols = df[['prev_1', 'prev_2', 'prev_3']].astype(int)
    X = pd.concat([prev_cols, category_dummies], axis=1)
    y = df['status'].astype(int)

    print("3. Splitting data into Training and Testing sets...")
    # 80% of data to train the AI, 20% to test it like a final exam
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("4. Training the Random Forest AI Model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    print("5. Evaluating the AI...")
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    
    print(f"\n--- AI Model Results ---")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print("\nDetailed Report:")
    print(classification_report(y_test, predictions))

    print("6. Saving the 'Brain' to your project folder...")
    # Saves trained model as a file so web app can use it later without retraining
    joblib.dump(model, 'lightpath_ai_model.pkl')
    print("Success! 'lightpath_ai_model.pkl' has been saved.")

if __name__ == '__main__':
    train_lightpath_ai()