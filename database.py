import sqlite3
import time
from datetime import datetime

DB_NAME = "bot.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            facts_count INTEGER DEFAULT 0,
            gpt_messages INTEGER DEFAULT 0,
            quiz_games INTEGER DEFAULT 0,
            quiz_best_score INTEGER DEFAULT 0,
            resume_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id INTEGER,
            action TEXT,
            timestamp REAL,
            PRIMARY KEY (user_id, action, timestamp)
        )
    """)

    conn.commit()
    conn.close()


def save_user(user_id, username=None, first_name=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()


def update_stat(user_id, stat_name, increment=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO user_stats (user_id) VALUES (?)", (user_id,))
    cursor.execute(f"""
        UPDATE user_stats SET {stat_name} = {stat_name} + ? WHERE user_id = ?
    """, (increment, user_id))
    conn.commit()
    conn.close()


def save_quiz_score(user_id, topic, score):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quiz_scores (user_id, topic, score) VALUES (?, ?, ?)
    """, (user_id, topic, score))

    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO user_stats (user_id) VALUES (?)", (user_id,))

    cursor.execute("""
        UPDATE user_stats SET quiz_best_score = MAX(quiz_best_score, ?) WHERE user_id = ?
    """, (score, user_id))

    conn.commit()
    conn.close()


def get_user_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            'facts_count': 0,
            'gpt_messages': 0,
            'quiz_games': 0,
            'quiz_best_score': 0,
            'resume_count': 0
        }
    return dict(row)


def check_rate_limit(user_id, action, max_per_minute=10):
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = time.time() - 60
    cursor.execute("""
        DELETE FROM rate_limits WHERE user_id = ? AND action = ? AND timestamp < ?
    """, (user_id, action, cutoff))
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM rate_limits WHERE user_id = ? AND action = ?
    """, (user_id, action))
    row = cursor.fetchone()
    count = row['cnt'] if row else 0
    if count >= max_per_minute:
        conn.commit()
        conn.close()
        return False
    cursor.execute("""
        INSERT INTO rate_limits (user_id, action, timestamp) VALUES (?, ?, ?)
    """, (user_id, action, time.time()))
    conn.commit()
    conn.close()
    return True
