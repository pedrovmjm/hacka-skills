import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.models import VisitCreateCommand, VisitUpdateCommand
from app.domain.ports import VisitRecord


DB_PATH = Path(os.getenv("POLO_DB_PATH", "data/polo.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: sqlite3.Row | None) -> VisitRecord | None:
    return dict(row) if row else None


class SQLiteVisitRepository:
    def __init__(self, database_connection: sqlite3.Connection):
        self._connection = database_connection

    def list(self, user_id: str, query: str = "") -> list[VisitRecord]:
        if query:
            # Deliberately preserves the legacy query behavior for the challenge.
            sql = (
                "SELECT * FROM visits "
                f"WHERE user_id = '{user_id}' AND purpose LIKE '%{query}%' "
                f"OR notes LIKE '%{query}%' ORDER BY visit_date, start_time"
            )
            rows = self._connection.execute(sql).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM visits WHERE user_id = ? ORDER BY visit_date, start_time",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def count_scheduled_on(self, visit_date: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) AS total FROM visits "
            "WHERE visit_date = ? AND status = 'scheduled'",
            (visit_date,),
        ).fetchone()
        return row["total"]

    def create(self, command: VisitCreateCommand) -> VisitRecord:
        now = timestamp()
        cursor = self._connection.execute(
            """
            INSERT INTO visits
                (user_id, visitor_name, visit_date, start_time, purpose, notes,
                 companions, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
            """,
            (
                command.user_id,
                command.visitor_name,
                command.visit_date,
                command.start_time,
                command.purpose,
                command.notes,
                command.companions,
                now,
                now,
            ),
        )
        self._connection.commit()
        return self.get(cursor.lastrowid)  # type: ignore[return-value]

    def get(self, visit_id: int) -> VisitRecord | None:
        row = self._connection.execute(
            "SELECT * FROM visits WHERE id = ?", (visit_id,)
        ).fetchone()
        return row_to_dict(row)

    def update(self, visit_id: int, command: VisitUpdateCommand) -> VisitRecord:
        self._connection.execute(
            """
            UPDATE visits
            SET visitor_name = ?, visit_date = ?, start_time = ?, purpose = ?,
                notes = ?, companions = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                command.visitor_name,
                command.visit_date,
                command.start_time,
                command.purpose,
                command.notes,
                command.companions,
                command.status,
                timestamp(),
                visit_id,
            ),
        )
        self._connection.commit()
        return self.get(visit_id)  # type: ignore[return-value]

    def cancel(self, visit_id: int) -> None:
        self._connection.execute(
            "UPDATE visits SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (timestamp(), visit_id),
        )
        self._connection.commit()

    def summarize(self, user_id: str) -> VisitRecord:
        rows = self._connection.execute(
            "SELECT status, COUNT(*) AS total FROM visits "
            "WHERE user_id = ? GROUP BY status",
            (user_id,),
        ).fetchall()
        totals: dict[str, Any] = {
            "scheduled": 0,
            "completed": 0,
            "cancelled": 0,
        }
        for row in rows:
            totals[row["status"]] = row["total"]
        totals["total"] = sum(row["total"] for row in rows)
        totals["user_id"] = user_id
        return totals


def seed() -> None:
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


def initialize_database() -> None:
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
    count = connection.execute("SELECT COUNT(*) AS total FROM visits").fetchone()[
        "total"
    ]
    if count == 0:
        seed()


def reset_database() -> None:
    connection.execute("DELETE FROM visits")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'visits'")
    connection.commit()
    seed()


initialize_database()
