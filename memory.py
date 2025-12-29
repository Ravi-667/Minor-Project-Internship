import sqlite3
import json
import os

DB_PATH = "chat_history.db"

def init_db():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_message(role, content):
    """Adds a new message to the history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def get_recent_history(limit=5):
    """Retrieves the last N messages formatted for the AI."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT role, content FROM messages ORDER BY id DESC LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    
    history_str = ""
    for role, content in reversed(rows):
        history_str += f"{role.capitalize()}: {content}\n"
    return history_str

# --- NEW FUNCTION: CLEAR DATABASE ---
def clear_db():
    """Deletes all messages to start a fresh session."""
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages") # Wipes data, keeps table structure
            conn.commit()
            conn.close()
            print("🧹 SQL Chat History Cleared.")
    except Exception as e:
        print(f"⚠️ Error clearing DB: {e}")

# Initialize on import
init_db()