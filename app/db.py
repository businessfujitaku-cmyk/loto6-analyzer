"""SQLite database layer for LOTO6 draw history."""

import sqlite3
import os
import threading
from typing import List, Dict, Optional

DB_PATH = os.environ.get("LOTO6_DB", os.path.join(os.path.dirname(__file__), "..", "loto6.db"))

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db() -> None:
    c = _conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            round   INTEGER PRIMARY KEY,
            date    TEXT NOT NULL,
            n1 INTEGER, n2 INTEGER, n3 INTEGER,
            n4 INTEGER, n5 INTEGER, n6 INTEGER,
            bonus   INTEGER
        )
    """)
    c.commit()


def insert_rows(rows: List[Dict]) -> int:
    c = _conn()
    added = 0
    for r in rows:
        try:
            c.execute(
                "INSERT OR IGNORE INTO draws (round, date, n1, n2, n3, n4, n5, n6, bonus) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["round"], r["date"], r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"], r["bonus"]),
            )
            if c.total_changes and c.execute("SELECT changes()").fetchone()[0] > 0:
                added += 1
        except sqlite3.IntegrityError:
            pass
    c.commit()
    return added


def count_rows() -> int:
    return _conn().execute("SELECT COUNT(*) FROM draws").fetchone()[0]


def latest_round() -> Optional[int]:
    row = _conn().execute("SELECT MAX(round) FROM draws").fetchone()
    return row[0] if row and row[0] else None


def latest_draw() -> Optional[Dict]:
    row = _conn().execute(
        "SELECT * FROM draws ORDER BY round DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return {
        "round": row["round"],
        "date": row["date"],
        "numbers": [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]],
        "bonus": row["bonus"],
    }


def all_draws() -> List[Dict]:
    rows = _conn().execute("SELECT * FROM draws ORDER BY round ASC").fetchall()
    result = []
    for row in rows:
        result.append({
            "round": row["round"],
            "date": row["date"],
            "numbers": [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]],
            "bonus": row["bonus"],
        })
    return result
