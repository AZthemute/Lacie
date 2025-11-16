import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "databases")

# Create databases directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)

def get_db(db_type="lifetime"):
    """
    Get database connection based on type.
    
    Args:
        db_type: "lifetime", "annual", "monthly", "weekly", or "daily"
              Can also be a boolean (True for lifetime, False for annual) for backwards compatibility
    """
    # Handle backwards compatibility with boolean argument
    if isinstance(db_type, bool):
        db_type = "lifetime" if db_type else "annual"
    
    valid_types = ["lifetime", "annual", "monthly", "weekly", "daily"]
    if db_type not in valid_types:
        db_type = "lifetime"
    
    db_name = f"{db_type}.db"
    db_path = os.path.join(DB_DIR, db_name)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Only create tables if they don't exist (won't modify existing tables)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS xp (
        user_id TEXT PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        last_message INTEGER DEFAULT 0
    )
    """)
    
    # Store last reset time for time-based leaderboards ONLY
    # This won't affect lifetime or annual databases
    if db_type in ["daily", "weekly", "monthly"]:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reset_log (
            id INTEGER PRIMARY KEY,
            last_reset INTEGER DEFAULT 0
        )
        """)
        cur.execute("INSERT OR IGNORE INTO reset_log (id, last_reset) VALUES (1, 0)")
    
    conn.commit()
    return conn, cur

def reset_leaderboard(db_type):
    """Reset a time-based leaderboard."""
    import time
    
    conn, cur = get_db(db_type)
    cur.execute("DELETE FROM xp")
    cur.execute("UPDATE reset_log SET last_reset = ? WHERE id = 1", (int(time.time()),))
    conn.commit()
    conn.close()

def get_last_reset(db_type):
    """Get the last reset time for a leaderboard."""
    conn, cur = get_db(db_type)
    cur.execute("SELECT last_reset FROM reset_log WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0