import sqlite3
from config import DB_PATH

conn = sqlite3.connect(DB_PATH, check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS indexes (
    index_id TEXT PRIMARY KEY,
    url TEXT,
    collection_name TEXT,
    status TEXT
)
""")

conn.commit()


def save_index(index_id, url, collection_name, status):
    conn.execute(
        "INSERT OR REPLACE INTO indexes VALUES (?, ?, ?, ?)",
        (index_id, url, collection_name, status)
    )
    conn.commit()


def get_index(index_id):
    cur = conn.execute(
        "SELECT * FROM indexes WHERE index_id=?",
        (index_id,)
    )
    return cur.fetchone()