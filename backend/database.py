import sqlite3
from datetime import datetime

conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS repos (
    repo_id TEXT PRIMARY KEY,
    repo_url TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT,
    user_message TEXT,
    bot_response TEXT,
    timestamp TEXT
)
""")

conn.commit()

def save_repo(repo_id, repo_url):
    cursor.execute(
        "INSERT INTO repos VALUES (?, ?, ?)",
        (repo_id, repo_url, datetime.now())
    )
    conn.commit()


def get_repo(repo_id):
    cursor.execute(
        "SELECT * FROM repos WHERE repo_id=?",
        (repo_id,)
    )
    return cursor.fetchone()


def save_chat(repo_id, user_message, bot_response):
    cursor.execute(
        """
        INSERT INTO chats (repo_id, user_message, bot_response, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (repo_id, user_message, bot_response, datetime.now())
    )
    conn.commit()


def get_chat_history(repo_id):
    cursor.execute(
        """
        SELECT user_message, bot_response
        FROM chats
        WHERE repo_id=?
        ORDER BY id ASC
        """,
        (repo_id,)
    )
    return cursor.fetchall()

def delete_repo(repo_id):
    cursor.execute("DELETE FROM chats WHERE repo_id=?", (repo_id,))
    cursor.execute("DELETE FROM repos WHERE repo_id=?", (repo_id,))
    conn.commit()