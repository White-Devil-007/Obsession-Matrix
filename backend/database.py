import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional, Union
from pathlib import Path
from backend.config import DB_PATH, DEFAULT_SETTINGS

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS interests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER NULL,
    is_current_obsession INTEGER DEFAULT 0,
    custom_progress TEXT DEFAULT 'Not Started',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES interests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interest_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'not_started',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interest_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT 'Progress Update',
    description TEXT DEFAULT '',
    progress_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE
);
"""

class Database:
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = str(db_path or DB_PATH)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_cursor() as cursor:
            cursor.executescript(SCHEMA_SQL)
            # Seed default settings if not exists
            for key, val in DEFAULT_SETTINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, val)
                )
            # Migration: add title/description columns if missing (existing DBs)
            cursor.execute("PRAGMA table_info(progress_logs)")
            cols = [row[1] for row in cursor.fetchall()]
            if "title" not in cols:
                cursor.execute("ALTER TABLE progress_logs ADD COLUMN title TEXT NOT NULL DEFAULT 'Progress Update'")
            if "description" not in cols:
                cursor.execute("ALTER TABLE progress_logs ADD COLUMN description TEXT DEFAULT ''")

# Global DB Singleton
_db_instance: Optional[Database] = None

def get_db(db_path: Optional[Union[str, Path]] = None) -> Database:
    global _db_instance
    if _db_instance is None or db_path is not None:
        _db_instance = Database(db_path)
    return _db_instance
