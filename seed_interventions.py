"""Seeds the intervention_library with a wide, multi-worldview bench of nudges.

Schema reminder: (category, type, message, source, tags)

CATEGORY  drives habit-area matching: Health / Learning / Productivity / General
TYPE      is a freeform label shown to the user ("physiology", "wisdom"…)
TAGS      drive worldview filtering (comma-separated):
    universal   — safe for anyone (physiology, science, plain encouragement)
    secular     — non-religious philosophical / motivational
    stoic       — Marcus Aurelius, Seneca, Epictetus
    christian   — biblical scripture / Christian writers
    islamic     — Qur'an / Hadith / Islamic sayings
    buddhist    — Buddhist teaching / sutras
    hindu       — Bhagavad Gita / Hindu teaching
    jewish      — Tanakh / Talmud / Jewish wisdom
    eastern     — broader East Asian wisdom (Lao Tzu, Confucius)
    african     — African proverbs and writers
    indigenous  — Native / indigenous wisdom

Insight engine rules (see app.py):
- religion = None / Atheist / Agnostic → exclude any specifically religious tag
- religion = Christianity → include 'christian', plus 'universal' and 'secular'
- religion = Islam → include 'islamic', plus 'universal' and 'secular'
- religion = Buddhism → include 'buddhist' + 'eastern' + 'universal'
- religion = Hinduism → include 'hindu' + 'eastern' + 'universal'
- religion = Judaism → include 'jewish' + 'universal'
- religion = Other / Spiritual → include all spiritual tags + 'universal'
- religion = "Prefer not to say" → 'universal' + 'secular'

Run `python seed_interventions.py` any time to refresh the library.
"""
import sqlite3

DATABASE = 'lightpath.db'


def seed_database():
    print("=== TheLightPath: seeding the multi-worldview encouragement library ===")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Ensure the table exists with the new shape
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
    cursor.execute('DELETE FROM intervention_library')

    rows = [
        # ============================== HEALTH ==============================
        # --- universal: physiology, sleep, hydration, movement ---
        ("Health", "physiology",
         "Even mild dehydration (just 2% of body water) measurably dulls attention and short-term memory. A glass of water is the cheapest cognitive upgrade you own.",
         "Journal of the American College of Nutrition", "universal"),
        ("Health", "physiology",
         "Ten minutes of brisk walking lifts mood for up to two hours. The smallest dose still works.",
         "British Journal of Sports Medicine", "universal"),
        ("Health", "physiology",
         "Your body literally rebuilds itself while you sleep. Skimping on rest is skimping on tomorrow's version of you.",
         None, "universal"),
        ("Health", "physiology",
         "Sunlight in the first hour after waking calibrates your body clock for the whole day. Step outside for two minutes before reaching for your phone.",
         "Andrew Huberman, Stanford", "universal"),
        ("Health", "physiology",
         "A short, slow exhale (longer out than in) activates the parasympathetic nervous system. Three of those and you've physically calmed yourself down.",
         None, "universal"),
        ("Health", "physiology",
         "Strength training twice a week is the single best-evidenced intervention against age-related muscle loss. Even ten minutes counts.",
         "British Journal of Sports Medicine", "universal"),
        ("Health", "psychology",
         "The neuroscience of habit favours friction. Lay your gym kit out tonight and tomorrow morning's decision is already half made.",
         None, "universal"),
        ("Health", "psychology",
         "If a workout feels too big, shrink it. Two minutes counts. Showing up is the actual habit; intensity follows later.",
         "Atomic Habits", "universal"),
        ("Health", "practical",
         "If you can't face the full habit today, do the two-minute version. Tomorrow's you will still thank you.",
         None, "universal"),
        ("Health", "practical",
         "Posture check: shoulders back, jaw soft, one slow breath. A reset is free and takes five seconds.",
         None, "universal"),
        ("Health", "practical",
         "Eat one piece of real, recognisable food before anything ultra-processed today. The smallest swap is still a swap.",
         None, "universal"),
        # --- stoic / secular ---
        ("Health", "philosophy",
         "Strength does not come from physical capacity. It comes from an indomitable will.",
         "Mahatma Gandhi", "secular,universal"),
        ("Health", "philosophy",
         "First say to yourself what you would be; and then do what you have to do.",
         "Epictetus", "stoic,secular"),
        ("Health", "philosophy",
         "It is health that is real wealth and not pieces of gold and silver.",
         "Mahatma Gandhi", "secular,universal"),
        # --- christian ---
        ("Health", "scripture",
         "Do you not know that your bodies are temples of the Holy Spirit? Honour what you've been given today.",
         "1 Corinthians 6:19-20", "christian"),
        ("Health", "scripture",
         "Whether you eat or drink or whatever you do, do it all for the glory of God.",
         "1 Corinthians 10:31", "christian"),
        # --- islamic ---
        ("Health", "scripture",
         "Your body has a right over you.",
         "Hadith — Sahih al-Bukhari", "islamic"),
        ("Health", "scripture",
         "Eat and drink, but be not excessive — surely He does not love those who are excessive.",
         "Qur'an 7:31", "islamic"),
        # --- buddhist ---
        ("Health", "philosophy",
         "To keep the body in good health is a duty, otherwise we shall not be able to keep our mind strong and clear.",
         "The Buddha", "buddhist,eastern"),
        ("Health", "philosophy",
         "What we think, we become. Care for the body so the mind has somewhere clean to live.",
         "Buddhist tradition", "buddhist,eastern"),
        # --- hindu ---
        ("Health", "philosophy",
         "When meditation is mastered, the mind is unwavering like the flame of a lamp in a windless place.",
         "Bhagavad Gita 6.19", "hindu,eastern"),
        # --- jewish ---
        ("Health", "scripture",
         "Take utmost care and watch yourselves scrupulously.",
         "Deuteronomy 4:9", "jewish"),
        # --- african / wisdom ---
        ("Health", "wisdom",
         "He who has health has hope, and he who has hope has everything.",
         "Arabian proverb", "universal,secular"),
        ("Health", "wisdom",
         "Health is not valued till sickness comes.",
         "African proverb", "african,universal"),
        ("Health", "wisdom",
         "Take care of your body. It's the only place you have to live.",
         "Jim Rohn", "secular,universal"),

        # ============================== LEARNING ==============================
        ("Learning", "psychology",
         "Spaced learning beats cramming. Twenty minutes today, twenty tomorrow — your brain consolidates between sessions, not during them.",
         "Ebbinghaus forgetting curve", "universal"),
        ("Learning", "psychology",
         "Testing yourself is the act of learning, not just measuring it. Close the book and try to recall — that's where the deep wiring happens.",
         "The Testing Effect, Roediger & Karpicke", "universal"),
        ("Learning", "psychology",
         "Confusion is not failure. It's the precise feeling of your brain about to grow.",
         None, "universal"),
        ("Learning", "psychology",
         "Switch where you study every now and then. Varied contexts make memory more robust.",
         "Bjork lab", "universal"),
        ("Learning", "practical",
         "Read one page. Just one. Often the page reads you back.",
         None, "universal"),
        ("Learning", "practical",
         "Don't aim for an hour. Aim to open the book. The hour usually shows up on its own.",
         None, "universal"),
        ("Learning", "practical",
         "Teach it to an imaginary friend. If you stumble, that's the part you don't actually know yet.",
         "Feynman technique", "universal"),
        # philosophy
        ("Learning", "philosophy",
         "Knowing yourself is the beginning of all wisdom.",
         "Aristotle", "secular,stoic"),
        ("Learning", "philosophy",
         "I am still learning.",
         "Michelangelo, age 87", "secular"),
        ("Learning", "philosophy",
         "Education is the kindling of a flame, not the filling of a vessel.",
         "Socrates", "secular,stoic"),
        ("Learning", "philosophy",
         "He who learns but does not think is lost. He who thinks but does not learn is in great danger.",
         "Confucius", "eastern,secular"),
        ("Learning", "wisdom",
         "The expert in anything was once a beginner who refused to quit.",
         None, "universal"),
        ("Learning", "wisdom",
         "Live as if you were to die tomorrow. Learn as if you were to live forever.",
         "Mahatma Gandhi", "secular,universal"),
        # christian
        ("Learning", "scripture",
         "Apply your heart to instruction and your ears to words of knowledge.",
         "Proverbs 23:12", "christian"),
        ("Learning", "scripture",
         "An intelligent heart acquires knowledge, and the ear of the wise seeks knowledge.",
         "Proverbs 18:15", "christian"),
        # islamic
        ("Learning", "scripture",
         "Seek knowledge from the cradle to the grave.",
         "Hadith", "islamic"),
        ("Learning", "scripture",
         "And say: My Lord, increase me in knowledge.",
         "Qur'an 20:114", "islamic"),
        # buddhist
        ("Learning", "philosophy",
         "An idea that is developed and put into action is more important than an idea that exists only as an idea.",
         "The Buddha", "buddhist,eastern"),
        # hindu
        ("Learning", "scripture",
         "He who has faith, who is devoted to it, and who has subdued his senses, obtains knowledge.",
         "Bhagavad Gita 4.39", "hindu,eastern"),
        # jewish
        ("Learning", "scripture",
         "Who is wise? He who learns from every person.",
         "Pirkei Avot 4:1", "jewish"),
        # african
        ("Learning", "wisdom",
         "However long the night, the dawn will break.",
         "African proverb", "african,universal"),
        ("Learning", "wisdom",
         "If you want to go fast, go alone. If you want to go far, go together.",
         "African proverb", "african,universal"),

        # ============================== PRODUCTIVITY ==============================
        ("Productivity", "psychology",
         "Motivation follows action far more often than the other way round. Start the task badly — it will improve as you go.",
         None, "universal"),
        ("Productivity", "psychology",
         "Procrastination is rarely about laziness. It's almost always an unspoken fear of doing the thing imperfectly. Lower the bar.",
         None, "universal"),
        ("Productivity", "psychology",
         "The Zeigarnik effect: unfinished tasks weigh on the mind. Even five minutes of progress lifts the load.",
         "Bluma Zeigarnik", "universal"),
        ("Productivity", "wisdom",
         "Don't rely on motivation. Rely on your system. Aim for 1% better — and never let yourself drop to zero.",
         "Atomic Habits", "secular,universal"),
        ("Productivity", "wisdom",
         "Do the hard thing first. The rest of the day will thank you for it.",
         "Eat That Frog, Brian Tracy", "secular,universal"),
        ("Productivity", "wisdom",
         "You don't rise to the level of your goals; you fall to the level of your systems.",
         "James Clear", "secular,universal"),
        ("Productivity", "practical",
         "Set a five-minute timer. Five honest minutes almost always becomes more.",
         "Pomodoro technique", "universal"),
        ("Productivity", "practical",
         "Close all the tabs except the one. Friction works in your favour and against you — decide which side it's on.",
         None, "universal"),
        ("Productivity", "practical",
         "Write down the next single action. Not the goal, the action. Then do that.",
         "Getting Things Done", "universal"),
        # stoic
        ("Productivity", "philosophy",
         "What stands in the way becomes the way.",
         "Marcus Aurelius", "stoic,secular"),
        ("Productivity", "philosophy",
         "Well begun is half done.",
         "Aristotle", "secular,stoic"),
        ("Productivity", "philosophy",
         "It is not the man who has too little, but the man who craves more, that is poor.",
         "Seneca", "stoic,secular"),
        ("Productivity", "philosophy",
         "We suffer more often in imagination than in reality.",
         "Seneca", "stoic,secular"),
        # christian
        ("Productivity", "scripture",
         "Go to the ant, you sluggard; consider its ways and be wise. It stores its provisions in summer.",
         "Proverbs 6:6-8", "christian"),
        ("Productivity", "scripture",
         "Whatever your hand finds to do, do it with all your might.",
         "Ecclesiastes 9:10", "christian"),
        ("Productivity", "scripture",
         "Awake, O sleeper, and arise. Resist complacency today.",
         "Ephesians 5:14", "christian"),
        # islamic
        ("Productivity", "scripture",
         "Indeed, with hardship comes ease.",
         "Qur'an 94:6", "islamic"),
        ("Productivity", "scripture",
         "Take advantage of five before five: your youth before your old age, your health before your sickness, your wealth before your poverty, your free time before your busyness, and your life before your death.",
         "Hadith", "islamic"),
        # buddhist
        ("Productivity", "philosophy",
         "Do not dwell in the past, do not dream of the future, concentrate the mind on the present moment.",
         "The Buddha", "buddhist,eastern"),
        ("Productivity", "philosophy",
         "A jug fills drop by drop.",
         "The Buddha", "buddhist,eastern"),
        # hindu
        ("Productivity", "scripture",
         "You have the right to work, but never to the fruit of work. Do your duty, but do not anchor it to outcomes.",
         "Bhagavad Gita 2.47", "hindu,eastern"),
        # jewish
        ("Productivity", "scripture",
         "You are not obligated to complete the work, but neither are you free to abandon it.",
         "Pirkei Avot 2:16", "jewish"),
        # eastern
        ("Productivity", "wisdom",
         "The journey of a thousand miles begins with a single step.",
         "Lao Tzu", "eastern,secular,universal"),
        ("Productivity", "wisdom",
         "When the student is ready, the teacher appears.",
         "Lao Tzu", "eastern,secular"),

        # ============================== GENERAL (universal default) ==============================
        ("General", "wisdom",
         "You are not behind. You are not ahead. You are exactly where the next right step begins.",
         None, "universal"),
        ("General", "wisdom",
         "Small habits, repeated, become an identity. Every check-in is a vote for the person you want to be.",
         "Atomic Habits", "secular,universal"),
        ("General", "wisdom",
         "Discipline is choosing between what you want now and what you want most.",
         "Abraham Lincoln", "secular,universal"),
        ("General", "wisdom",
         "The two most powerful warriors are patience and time.",
         "Leo Tolstoy", "secular,universal"),
        ("General", "wisdom",
         "On hard days, lower the standard, not the streak. Showing up imperfectly still counts.",
         None, "universal"),
        ("General", "wisdom",
         "Lighting up one habit today doesn't cancel a slip yesterday — it begins a new line. Every day is fresh.",
         None, "universal"),
        ("General", "wisdom",
         "Comparison steals the path. Yours is the only one you can walk.",
         None, "universal"),
        ("General", "encouragement",
         "You are doing better than you think. The fact that you opened this page is itself the habit.",
         None, "universal"),
        ("General", "encouragement",
         "Whatever happened yesterday, the path is still here. So are you.",
         None, "universal"),
        ("General", "encouragement",
         "Bright days are built in dim moments. Keep going.",
         None, "universal"),
        ("General", "encouragement",
         "One brave, small thing. That's all today is asking for.",
         None, "universal"),
        ("General", "encouragement",
         "Light another corner of your day. The whole room brightens.",
         None, "universal"),
        ("General", "encouragement",
         "Rest is not the opposite of progress. It's part of it.",
         None, "universal"),
        ("General", "psychology",
         "Make the next decision the easy one. Set out your shoes, lay out the book, open the document. Future-you is grateful.",
         None, "universal"),
        ("General", "psychology",
         "Identity-based habits stick. Don't say 'I'm trying to read more'. Say 'I'm a reader' — then read one page.",
         "James Clear", "secular,universal"),
        ("General", "psychology",
         "The opposite of giving up isn't pushing harder. It's gentler self-talk and a smaller next step.",
         None, "universal"),
        # stoic
        ("General", "philosophy",
         "You have power over your mind — not outside events. Realise this, and you will find strength.",
         "Marcus Aurelius", "stoic,secular"),
        ("General", "philosophy",
         "Difficulties strengthen the mind, as labour does the body.",
         "Seneca", "stoic,secular"),
        ("General", "philosophy",
         "The strength of a man's virtues is made up of his habitual acts.",
         "Blaise Pascal", "secular,universal"),
        ("General", "philosophy",
         "The second half of a man's life is made up of the habits he acquired in the first half.",
         "Fyodor Dostoevsky", "secular,universal"),
        # christian
        ("General", "scripture",
         "Let us not grow weary of doing good, for in due season we will reap, if we do not give up.",
         "Galatians 6:9", "christian"),
        ("General", "scripture",
         "Commit to the Lord whatever you do, and he will establish your plans.",
         "Proverbs 16:3", "christian"),
        ("General", "scripture",
         "The path of the righteous is like the morning sun, shining ever brighter till the full light of day.",
         "Proverbs 4:18", "christian"),
        ("General", "scripture",
         "Be strong and courageous. Do not be afraid; do not be discouraged.",
         "Joshua 1:9", "christian"),
        # islamic
        ("General", "scripture",
         "Allah does not burden a soul beyond that it can bear.",
         "Qur'an 2:286", "islamic"),
        ("General", "scripture",
         "The most beloved of deeds to Allah are those that are most consistent, even if they are small.",
         "Hadith — Sahih al-Bukhari", "islamic"),
        ("General", "scripture",
         "And whoever puts their trust in Allah — He is sufficient for them.",
         "Qur'an 65:3", "islamic"),
        # buddhist
        ("General", "philosophy",
         "Drop by drop is the water pot filled. Likewise, the wise man, gathering it little by little, fills himself with good.",
         "Dhammapada 9.122", "buddhist,eastern"),
        ("General", "philosophy",
         "Peace comes from within. Do not seek it without.",
         "The Buddha", "buddhist,eastern"),
        ("General", "philosophy",
         "You yourself, as much as anybody in the entire universe, deserve your love and affection.",
         "The Buddha", "buddhist,eastern"),
        # hindu
        ("General", "scripture",
         "Whenever the mind, restless and unsteady, wanders away — gently bring it back. That bringing-back is the practice.",
         "Bhagavad Gita 6.26", "hindu,eastern"),
        ("General", "scripture",
         "The soul is neither born, nor does it die. What is real cannot be destroyed.",
         "Bhagavad Gita 2.20", "hindu,eastern"),
        # jewish
        ("General", "scripture",
         "If I am not for myself, who will be for me? If I am only for myself, what am I? And if not now, when?",
         "Hillel — Pirkei Avot 1:14", "jewish"),
        # eastern
        ("General", "wisdom",
         "Be water, my friend. Empty your mind, be formless, shapeless.",
         "Bruce Lee", "eastern,secular"),
        # african
        ("General", "wisdom",
         "Smooth seas do not make skilful sailors.",
         "African proverb", "african,universal"),
        ("General", "wisdom",
         "Until the lion learns to write, every story will glorify the hunter — write your own story today.",
         "African proverb", "african,universal"),
        # indigenous
        ("General", "wisdom",
         "What is life? It is the flash of a firefly in the night. It is the breath of a buffalo in the wintertime. Make it count today.",
         "Crowfoot, Blackfoot chief", "indigenous,universal"),
    ]

    cursor.executemany('''
        INSERT INTO intervention_library (category, type, message, source, tags)
        VALUES (?, ?, ?, ?, ?)
    ''', rows)

    conn.commit()
    conn.close()
    print(f"Success! {len(rows)} entries are in the encouragement library.")


if __name__ == '__main__':
    seed_database()
