import sqlite3

DATABASE = 'lightpath.db'

def seed_database():
    print("=== TheLightPath: Seeding Intervention Library ===")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Ensure the table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intervention_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT
        )
    ''')

    # Clear out any existing entries to prevent duplicates if run multiple times
    cursor.execute('DELETE FROM intervention_library')

    # The library of proactive interventions (Scriptures, Health Facts, Psychology)
    interventions = [
        # --- HEALTH CATEGORY ---
        ("Health", "physiological_fact", 
         "Dehydration by just 2% impairs cognitive performance in tasks that require attention and immediate memory skills. Go drink a glass of water right now.", 
         "Journal of the American College of Nutrition"),
        ("Health", "scripture", 
         "Do you not know that your bodies are temples of the Holy Spirit? Honour God with your body today.", 
         "1 Corinthians 6:19-20"),
        ("Health", "actionable_advice", 
         "The neuroscience of habit formation relies on reducing friction. Put your gym clothes or running shoes right next to your bed tonight.", 
         "Behavioural Psychology"),

        # --- LEARNING CATEGORY ---
        ("Learning", "psychological_advice", 
         "Utilise the 'Spacing Effect': you will retain significantly more information if you study in short, spaced-out bursts rather than one long, stressful cramming session.", 
         "The Ebbinghaus Forgetting Curve"),
        ("Learning", "scripture", 
         "Apply your heart to instruction and your ears to words of knowledge.", 
         "Proverbs 23:12"),
        ("Learning", "spiritual_encouragement", 
         "Pushing beyond initial resistance to do just a little bit more when you want to quit is the precise moment when true mental and spiritual discipline is formed.", 
         "Dag Heward-Mills"),

        # --- PRODUCTIVITY CATEGORY ---
        ("Productivity", "system_advice", 
         "Do not rely on fleeting motivation; fall back on your systems. Focus on making a 1% improvement today. Never go to zero.", 
         "Atomic Habits"),
        ("Productivity", "scripture", 
         "Go to the ant, you sluggard; consider its ways and be wise! It has no commander, yet it stores its provisions in summer.", 
         "Proverbs 6:6-8"),
        ("Productivity", "spiritual_awakening", 
         "Awake, O sleeper, and arise! You must actively resist complacency to fulfil your true potential today.", 
         "Ephesians 5:14 / Dag Heward-Mills")
    ]

    # Insert the data into the database
    cursor.executemany('''
        INSERT INTO intervention_library (category, type, message, source)
        VALUES (?, ?, ?, ?)
    ''', interventions)

    conn.commit()
    conn.close()
    
    print(f"Success! {len(interventions)} proactive interventions have been securely loaded into the database.")
    print("Your AI will now autonomously deploy these to users when their failure risk hits the 40% threshold.")

if __name__ == '__main__':
    seed_database()