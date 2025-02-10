# This is a script to generate random data after the first run of
# this application. After the `database.db` file has been created,
# you can run this script to generate random data to test the app.

import sqlite3
import random
from datetime import datetime, timedelta
import time

def create_database_schema():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute('DROP TABLE IF EXISTS chat_history')
    cursor.execute('DROP TABLE IF EXISTS mood_tracking')
    cursor.execute('DROP TABLE IF EXISTS user_progress')
    cursor.execute('DROP TABLE IF EXISTS activities')
    
    # Create activities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            points INTEGER DEFAULT 0,
            category TEXT
        )
    ''')
    
    # Create user_progress table - updated schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER,
            timestamp TEXT,
            completed BOOLEAN DEFAULT 1,
            points_earned INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities (id)
        )
    ''')
    
    # Mood Tracking Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            mood_score REAL,
            notes TEXT
        )
    ''')
    
    # Create chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            message TEXT,
            response TEXT,
            sentiment_score REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_sample_data():
    # Create schema first
    create_database_schema()
    
    # Connect to database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Sample activities with categories
    activities = [
        ("Morning Meditation", "Practiced mindfulness meditation for 10 minutes", 10, "mindfulness"),
        ("Nature Walk", "Took a refreshing walk in nature", 15, "exercise"),
        ("Gratitude Journaling", "Wrote down 3 things I'm grateful for", 10, "reflection"),
        ("Deep Breathing", "Practiced deep breathing exercises", 5, "mindfulness"),
        ("Social Call", "Called a friend or family member", 10, "social"),
        ("Art Session", "Drew or painted for relaxation", 15, "creative"),
        ("Positive Affirmations", "Practiced positive self-talk", 5, "mindfulness"),
        ("Exercise", "Did a workout or yoga session", 20, "exercise"),
        ("Reading", "Read a book for pleasure", 10, "mindfulness"),
        ("Music Break", "Listened to calming music", 5, "creative")
    ]
    
    # Insert activities
    cursor.execute('DELETE FROM activities')
    for activity in activities:
        cursor.execute('''
            INSERT INTO activities (name, description, points, category)
            VALUES (?, ?, ?, ?)
        ''', activity)
    
    # Generate 30 days of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    current_date = start_date
    
    # Clear existing data
    cursor.execute('DELETE FROM mood_tracking')  # Changed from mood_entries
    cursor.execute('DELETE FROM user_progress')
    cursor.execute('DELETE FROM chat_history')
    
    # Sample chat messages
    chat_messages = [
        "I'm feeling quite good today!",
        "Had a challenging day at work",
        "Feeling a bit anxious",
        "Made progress on my goals today",
        "Feeling motivated and energetic",
        "Need some support today",
        "Having a great day",
        "Feeling stressed but managing",
        "Today was productive",
        "Feeling peaceful after meditation"
    ]
    
    # Generate data for each day
    while current_date <= end_date:
        # Generate 1-3 activities per day
        daily_activities = random.sample(activities, random.randint(1, 3))
        for activity in daily_activities:
            timestamp = current_date.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59)
            )
            
            cursor.execute('''
                INSERT INTO user_progress (activity_id, timestamp, completed, points_earned)
                SELECT id, ?, 1, points
                FROM activities
                WHERE name = ?
            ''', (timestamp.isoformat(), activity[0]))
        
        # Generate mood entries (4-6 per day to ensure enough data)
        entry_count = random.randint(4, 6)
        for _ in range(entry_count):
            timestamp = current_date.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59)
            )
            # Generate mood score with a slight upward trend
            base_mood = 0.5 + ((current_date - start_date).days / 60)  # Gradual improvement
            mood_score = min(1.0, max(0.0, base_mood + random.uniform(-0.2, 0.2)))
            
            cursor.execute('''
                INSERT INTO mood_tracking (timestamp, mood_score, notes)
                VALUES (?, ?, ?)
            ''', (timestamp.isoformat(), mood_score, "Generated mood entry"))
        
        # Generate chat history (1-2 per day)
        chat_count = random.randint(1, 2)
        for _ in range(chat_count):
            timestamp = current_date.replace(
                hour=random.randint(8, 20),
                minute=random.randint(0, 59)
            )
            message = random.choice(chat_messages)
            response = f"I understand you're {message.lower()}. How can I help?"
            
            cursor.execute('''
                INSERT INTO chat_history (timestamp, message, response, sentiment_score)
                VALUES (?, ?, ?, ?)
            ''', (timestamp.isoformat(), message, response, random.uniform(0.3, 0.8)))
        
        current_date += timedelta(days=1)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Generating sample data...")
    generate_sample_data()
    print("Sample data generated successfully!")
