# app/models/db.py
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

BASE = Path(__file__).resolve().parents[2] / "app"
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "aktivitas.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nip TEXT UNIQUE,
        nama TEXT,
        email TEXT UNIQUE,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT CHECK(role IN ('admin','leader','programmer')) NOT NULL
    )
    """)
    # aktivitas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS aktivitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT,
        aplikasi TEXT,
        depo TEXT,
        tipe TEXT,
        collection TEXT,
        object TEXT,
        start_scheduler TEXT,
        finish_scheduler TEXT,
        start_bridge TEXT,
        finish_bridge TEXT,
        duration_minutes INTEGER,
        status TEXT,
        notes TEXT,
        scheduled_at TEXT,
        cluster INTEGER
    )
    """)
    # Indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aktivitas_tanggal ON aktivitas(tanggal)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aktivitas_cluster ON aktivitas(cluster)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.commit()
    # insert default admin if none
    cur.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        # default admin: username admin, password admin123 (hashed later by auth module if needed)
        cur.execute("INSERT INTO users (nip,nama,email,username,password,role) VALUES (?,?,?,?,?,?)",
                    ("000000", "Administrator", "admin@example.com", "admin", "admin123", "admin"))
        conn.commit()
    conn.close()

def backup_db():
    """Simple DB backup: copy with timestamp"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"aktivitas_backup_{ts}.db"
    shutil.copy2(DB_PATH, backup_path)
    return str(backup_path)

if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)
