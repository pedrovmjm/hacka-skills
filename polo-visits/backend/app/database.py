import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(os.getenv("POLO_DB_PATH", "data/polo.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            visitor_name TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            purpose TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            companions INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'scheduled',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    count = connection.execute("SELECT COUNT(*) AS total FROM visits").fetchone()["total"]
    if count == 0:
        seed()


def seed():
    created = timestamp()
    rows = [
        (
            "ana",
            "Ana Demo",
            "2026-10-05",
            "09:00",
            "Aula presencial",
            "Levar documento ficticio",
            0,
            "scheduled",
            created,
            created,
        ),
        (
            "bruno",
            "Bruno Demo",
            "2026-10-06",
            "14:00",
            "Atendimento academico",
            "Conferir sala na recepcao",
            1,
            "scheduled",
            created,
            created,
        ),
        (
            "ana",
            "Ana Demo",
            "2026-09-12",
            "10:30",
            "Encontro de projeto",
            "Visita ja concluida",
            0,
            "completed",
            created,
            created,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO visits
            (user_id, visitor_name, visit_date, start_time, purpose, notes,
             companions, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


def reset_database():
    connection.execute("DELETE FROM visits")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'visits'")
    connection.commit()
    seed()


def row_to_dict(row):
    return dict(row) if row else None


initialize_database()

