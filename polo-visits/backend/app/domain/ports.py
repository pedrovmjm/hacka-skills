from typing import Any, Protocol

from .models import AttendanceUpsertCommand


AttendanceRecord = dict[str, Any]
TeamMember = dict[str, str]


class AttendanceRepository(Protocol):
    def list_month(self, user_id: str, month: str) -> list[AttendanceRecord]: ...

    def upsert(self, command: AttendanceUpsertCommand) -> AttendanceRecord: ...

    def delete(self, user_id: str, attendance_date: str) -> None: ...

    def list_team(self, manager_id: str) -> list[TeamMember]: ...
