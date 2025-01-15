import sqlite3
from datetime import datetime
import threading

class Database:
    def __init__(self):
        self._local = threading.local()
        self.db_path = 'chats.db'
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_message TEXT,
                ai_response TEXT,
                sentiment REAL
            )
        ''')
        conn.commit()
        conn.close()

    def add_chat_entry(self, user_message, ai_response, sentiment=0.0):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (timestamp, user_message, ai_response, sentiment)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), user_message, ai_response, sentiment))
        conn.commit()

    def get_recent_chats(self, limit=10):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, user_message, ai_response
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
            SELECT timestamp, user_message, ai_response
            FROM chat_history
            ORDER BY timestamp ASC
        ''')
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn
