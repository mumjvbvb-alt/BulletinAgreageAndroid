import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 bon_number INTEGER UNIQUE NOT NULL,
 invoice_date TEXT NOT NULL,
 species TEXT NOT NULL,
 producer TEXT,
 address TEXT,
 producer_id TEXT,
 agreer TEXT,
 quantity_qx REAL,
 collection_point TEXT,
 status TEXT NOT NULL,
 data_json TEXT NOT NULL,
 layout_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS producers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT UNIQUE NOT NULL,
 address TEXT,
 identity_number TEXT
);
CREATE TABLE IF NOT EXISTS reasons (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 category TEXT NOT NULL,
 reason TEXT NOT NULL,
 UNIQUE(category, reason)
);
CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT);
"""

class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def next_bon_number(self):
        row = self.conn.execute("SELECT COALESCE(MAX(bon_number),0)+1 n FROM invoices").fetchone()
        return int(row["n"])

    def setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def save_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO app_settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
