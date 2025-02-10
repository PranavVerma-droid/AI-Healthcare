import sqlite3
from datetime import datetime, timedelta, timezone
import threading
import pytz  # type: ignore

class Database:
    def __init__(self):
        self._local = threading.local()
        self.db_path = 'database.db'
        self._init_db()
        self.timezone = pytz.timezone('Asia/Kolkata')

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Chat history table - fixed syntax error
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                message TEXT,
                response TEXT,
                sentiment_score REAL
            )
        ''')
        
        # Mood tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mood_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mood_score REAL,
                notes TEXT
            )
        ''')
        
        # Activities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                points INTEGER,
                category TEXT
            )
        ''')
        
        # User progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                activity_id INTEGER,
                completed BOOLEAN,
                points_earned INTEGER,
                FOREIGN KEY (activity_id) REFERENCES activities (id)
            )
        ''')
        
        # Activity notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER,
                timestamp TEXT,
                notes TEXT,
                FOREIGN KEY (activity_id) REFERENCES activities (id)
            )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM activities')
        if cursor.fetchone()[0] == 0:
            self._init_default_activities(cursor)
        
        conn.commit()
        conn.close()

    def _init_default_activities(self, cursor):
        default_activities = [
            ('Deep Breathing', 'Practice deep breathing for 5 minutes', 10, 'mindfulness'),
            ('Gratitude Journal', 'Write down 3 things you are grateful for', 15, 'reflection'),
            ('Walking', 'Take a 10-minute walk outside', 20, 'exercise'),
            ('Meditation', 'Complete a 5-minute guided meditation', 25, 'mindfulness'),
            ('Mood Check-in', 'Record your current mood and feelings', 5, 'tracking')
        ]
        cursor.executemany('''
            INSERT INTO activities (name, description, points, category)
            VALUES (?, ?, ?, ?)
        ''', default_activities)

    def _get_current_time(self):
        return datetime.now(self.timezone)

    def _format_date_for_db(self, date):
        if not date.tzinfo:
            date = self.timezone.localize(date)
        return date.strftime('%Y-%m-%d %H:%M:%S')

    def add_chat_entry(self, user_message, ai_response, sentiment=0.0):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (timestamp, message, response, sentiment_score)
            VALUES (?, ?, ?, ?)
        ''', (self._get_current_time().isoformat(), user_message, ai_response, sentiment))
        conn.commit()

    def get_recent_chats(self, limit=10):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, message, response
            FROM chat_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

    def clear_history(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_history')
        conn.commit()

    def get_all_chats(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, message, response
            FROM chat_history
            ORDER BY timestamp ASC
        ''')
        return cursor.fetchall()

    def add_mood_entry(self, mood_score, notes=""):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO mood_tracking (timestamp, mood_score, notes)
            VALUES (?, ?, ?)
        ''', (self._get_current_time().isoformat(), mood_score, notes))
        conn.commit()

    def get_weekly_mood_average(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        week_ago = (self._get_current_time() - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT AVG(mood_score)
            FROM mood_tracking
            WHERE timestamp > ?
        ''', (week_ago,))
        return cursor.fetchone()[0] or 0.0

    def get_daily_mood_average(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        today = self._get_current_time().date().isoformat()
        cursor.execute('''
            SELECT AVG(mood_score)
            FROM mood_tracking
            WHERE date(timestamp) = ?
        ''', (today,))
        return cursor.fetchone()[0] or 0.0

    def get_mood_trend(self, days=7):
        conn = self._get_conn()
        cursor = conn.cursor()
        start_date = (self._get_current_time() - timedelta(days=days-1)).date().isoformat()
        
        cursor.execute('''
            SELECT 
                date(timestamp) as day,
                AVG(mood_score) as avg_mood,
                COUNT(*)
                as entries
            FROM mood_tracking
            WHERE date(timestamp) >= ?
            GROUP BY date(timestamp)
            ORDER BY date(timestamp)
        ''', (start_date,))
        
        return cursor.fetchall()

    def get_activity_recommendations(self, current_mood):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # recommendations based on mood
        if current_mood < 0.3:  # Low mood
            category = 'mindfulness'
        elif current_mood < 0.7:  # Neutral mood
            category = 'exercise'
        else:  # Good mood
            category = 'reflection'
            
        cursor.execute('''
            SELECT DISTINCT a.name, a.description, a.points
            FROM activities a
            WHERE a.category = ?
            ORDER BY RANDOM()
            LIMIT 3
        ''', (category,))
        
        recommendations = cursor.fetchall()
        
        # recently completed activities
        cursor.execute('''
            SELECT DISTINCT a.name
            FROM user_progress p
            JOIN activities a ON p.activity_id = a.id
            WHERE p.timestamp > datetime('now', '-7 days')
            ORDER BY p.timestamp DESC
            LIMIT 5
        ''')
        recent = [row[0] for row in cursor.fetchall()]
        
        return recommendations, recent

    def add_generated_activity(self, activity_dict):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activities (name, description, points, category)
            VALUES (?, ?, ?, ?)
        ''', (
            activity_dict['name'],
            activity_dict['description'],
            activity_dict['points'],
            activity_dict['category']
        ))
        conn.commit()
        return cursor.lastrowid

    def complete_activity(self, activity_name):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = self._get_current_time()
        print(f"Completing activity at: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        cursor.execute('''
            SELECT id, points FROM activities WHERE name = ?
        ''', (activity_name,))
        activity = cursor.fetchone()
        if activity:
            activity_id, points = activity
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO user_progress (timestamp, activity_id, completed, points_earned)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, activity_id, True, points))
            conn.commit()
            return points
        return 0

    def get_total_points(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(points_earned) FROM user_progress')
        return cursor.fetchone()[0] or 0

    def get_weekly_progress(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        week_ago = (self._get_current_time() - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT a.name, COUNT(*), SUM(p.points_earned)
            FROM user_progress p
            JOIN activities a ON p.activity_id = a.id
            WHERE p.timestamp > ?
            GROUP BY a.name
        ''', (week_ago,))
        return cursor.fetchall()

    def add_activity_note(self, activity_name, notes):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM activities WHERE name = ?', (activity_name,))
        activity_id = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO activity_notes (activity_id, timestamp, notes)
            VALUES (?, ?, ?)
        ''', (activity_id, self._get_current_time().isoformat(), notes))
        conn.commit()

    def get_weekly_activities(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        today = self._get_current_time()
        start_of_week = (today - timedelta(days=today.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        
        print(f"Start of week: {start_of_week.strftime('%Y-%m-%d %H:%M:%S')}")
        
        cursor.execute('''
            WITH RECURSIVE dates(date) AS (
                SELECT date(?)
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date(?, '+6 day')
            )
            SELECT 
                CAST(strftime('%w', d.date) AS INTEGER) AS day_index,
                GROUP_CONCAT(a.name) as activities
            FROM dates d
            LEFT JOIN user_progress p ON date(p.timestamp) = d.date
            LEFT JOIN activities a ON p.activity_id = a.id
            WHERE d.date <= date(?)
            GROUP BY d.date
            ORDER BY d.date
        ''', (start_of_week.strftime('%Y-%m-%d'), 
              start_of_week.strftime('%Y-%m-%d'),
              today.strftime('%Y-%m-%d')))
        
        activities_by_day = {}
        for day, activities in cursor.fetchall():
            # convert Sunday from 0 to 6
            day_index = 6 if day == 0 else day - 1
            print(f"Day {day_index} ({day}): {activities}")
            if activities:
                activities_by_day[day_index] = activities.split(',')
        
        return activities_by_day

    def get_weekly_activity_count(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        week_ago = (self._get_current_time() - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT COUNT(*)
            FROM user_progress
            WHERE timestamp > ?
        ''', (week_ago,))
        return cursor.fetchone()[0] or 0

    def get_todays_activities(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        today_start = self._get_current_time().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = self._get_current_time().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        
        cursor.execute('''
            SELECT 
                a.name,
                a.category,
                p.points_earned,
                n.notes,
                p.timestamp
            FROM user_progress p
            JOIN activities a ON p.activity_id = a.id
            LEFT JOIN activity_notes n ON n.activity_id = a.id 
                AND datetime(n.timestamp) BETWEEN datetime(?) AND datetime(?)
            WHERE datetime(p.timestamp) BETWEEN datetime(?) AND datetime(?)
            ORDER BY p.timestamp DESC
        ''', (today_start, today_end, today_start, today_end))
        
        return cursor.fetchall()

    def get_day_activities(self, date):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if not date.tzinfo:
            date = self.timezone.localize(date)
        date = date.replace(tzinfo=None)
        
        cursor.execute('''
            SELECT 
                p.id,
                a.name,
                a.category,
                p.points_earned as points,
                n.notes,
                p.timestamp
            FROM user_progress p
            JOIN activities a ON p.activity_id = a.id
            LEFT JOIN activity_notes n ON n.activity_id = a.id 
            WHERE date(p.timestamp) = date(?)
            ORDER BY p.timestamp DESC
        ''', (date.strftime('%Y-%m-%d'),))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'points': row[3],
                'notes': row[4],
                'timestamp': row[5]
            })
        return activities

    def delete_activity(self, progress_id, date):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('BEGIN TRANSACTION')
        try:
            cursor.execute('''
                SELECT points_earned, activity_id
                FROM user_progress
                WHERE id = ?
            ''', (progress_id,))
            points, activity_id = cursor.fetchone()

            cursor.execute('DELETE FROM user_progress WHERE id = ?', (progress_id,))

            cursor.execute('''
                DELETE FROM activity_notes 
                WHERE activity_id = ? AND date(timestamp) = date(?)
            ''', (activity_id, date.isoformat()))

            cursor.execute('''
                UPDATE mood_tracking
                SET mood_score = mood_score - ?
                WHERE date(timestamp) = date(?)
            ''', (points * 0.01, date.isoformat()))  # adjust mood
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def close(self):
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn

    def get_activities_for_week(self, start_date):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if not start_date.tzinfo:
            start_date = self.timezone.localize(start_date)
        
        start_date = start_date.replace(tzinfo=None)
        end_date = (start_date + timedelta(days=6))
        
        print(f"Fetching activities from {start_date} to {end_date}")
        
        cursor.execute('''
            WITH RECURSIVE dates(date) AS (
                SELECT date(?)
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date(?, '+6 day')
            )
            SELECT 
                CAST(strftime('%w', d.date) AS INTEGER) AS day_index,
                GROUP_CONCAT(a.name) as activities
            FROM dates d
            LEFT JOIN user_progress p ON date(p.timestamp) = d.date
            LEFT JOIN activities a ON p.activity_id = a.id
            GROUP BY d.date
            ORDER BY d.date
        ''', (start_date.strftime('%Y-%m-%d'), start_date.strftime('%Y-%m-%d')))
        
        activities_by_day = {}
        for day, activities in cursor.fetchall():
            day_index = 6 if day == 0 else day - 1
            if activities:
                activities_by_day[day_index] = activities.split(',')
        
        return activities_by_day

    def get_stats_for_week(self, start_date):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if not start_date.tzinfo:
            start_date = self.timezone.localize(start_date)
        start_date = start_date.replace(tzinfo=None)
        end_date = (start_date + timedelta(days=6))
        
        cursor.execute('''
            SELECT COUNT(*) as activity_count, 
                   SUM(points_earned) as total_points
            FROM user_progress
            WHERE date(timestamp) BETWEEN date(?) AND date(?)
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        count_row = cursor.fetchone()
        
        # Get average mood
        cursor.execute('''
            SELECT AVG(mood_score)
            FROM mood_tracking
            WHERE date(timestamp) BETWEEN date(?) AND date(?)
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        mood_row = cursor.fetchone()
        
        return {
            'activity_count': count_row[0] or 0,
            'points': count_row[1] or 0,
            'mood_avg': mood_row[0] or 0.0
        }
