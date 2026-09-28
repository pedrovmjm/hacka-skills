import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from app.domain.models import AttendanceUpsertCommand
from app.domain.ports import AttendanceRecord, TeamMember


DB_PATH = Path(os.getenv("POLO_DB_PATH", "data/polo.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def row_to_dict(row: sqlite3.Row | None) -> AttendanceRecord | None:
    return dict(row) if row else None


class SQLiteAttendanceRepository:
    def __init__(self, database_connection: sqlite3.Connection):
        self._connection = database_connection

    def list_month(self, user_id: str, month: str) -> list[AttendanceRecord]:
        rows = self._connection.execute(
            "SELECT * FROM attendance "
            "WHERE user_id = ? AND substr(attendance_date, 1, 7) = ? "
            "ORDER BY attendance_date",
            (user_id, month),
        ).fetchall()
        return [dict(row) for row in rows]

    def upsert(self, command: AttendanceUpsertCommand) -> AttendanceRecord:
        now = timestamp()
        self._connection.execute(
            """
            INSERT INTO attendance
                (user_id, attendance_date, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, attendance_date) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                command.user_id,
                command.attendance_date,
                "present",
                command.notes,
                now,
                now,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM attendance WHERE user_id = ? AND attendance_date = ?",
            (command.user_id, command.attendance_date),
        ).fetchone()
        return row_to_dict(row)  # type: ignore[return-value]

    def delete(self, user_id: str, attendance_date: str) -> None:
        self._connection.execute(
            "DELETE FROM attendance WHERE user_id = ? AND attendance_date = ?",
            (user_id, attendance_date),
        )
        self._connection.commit()

    def list_team(self, manager_id: str) -> list[TeamMember]:
        rows = self._connection.execute(
            "SELECT user_id, name FROM team_members "
            "WHERE manager_id = ? ORDER BY name",
            (manager_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def seed() -> None:
    created = timestamp()
    month = current_month()
    connection.executemany(
        "INSERT INTO team_members (manager_id, user_id, name) VALUES (?, ?, ?)",
        [
            ("ana", "bruno", "Bruno Demo"),
            ("ana", "carla", "Carla Demo"),
            ("ana", "diego", "Diego Demo"),
        ],
    )
    attendance = [
        ("ana", f"{month}-02", "present", "Trabalho presencial"),
        ("ana", f"{month}-05", "present", "Reunião no polo"),
        ("bruno", f"{month}-01", "present", ""),
        ("bruno", f"{month}-03", "present", ""),
        ("carla", f"{month}-02", "present", ""),
        ("carla", f"{month}-04", "present", ""),
        ("carla", f"{month}-06", "present", ""),
        ("carla", f"{month}-10", "present", ""),
    ]
    connection.executemany(
        """
        INSERT INTO attendance
            (user_id, attendance_date, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(*row, created, created) for row in attendance],
    )
    connection.commit()


def initialize_database() -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS team_members (
            manager_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY(manager_id, user_id)
        );
        """
    )
    connection.execute("DELETE FROM attendance WHERE status != 'present'")
    connection.commit()
    count = connection.execute(
        "SELECT COUNT(*) AS total FROM attendance"
    ).fetchone()["total"]
    if count == 0:
        seed()


def reset_database() -> None:
    connection.execute("DELETE FROM attendance")
    connection.execute("DELETE FROM team_members")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'attendance'")
    connection.commit()
    seed()


initialize_database()
