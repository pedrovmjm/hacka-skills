from typing import Any

from app.domain.models import MONTHLY_GOAL, AttendanceUpsertCommand
from app.domain.ports import AttendanceRecord, AttendanceRepository


def monthly_summary(
    user_id: str, month: str, days: list[AttendanceRecord]
) -> dict[str, Any]:
    present_count = sum(day["status"] == "present" for day in days)
    absent_count = sum(day["status"] == "absent" for day in days)
    return {
        "user_id": user_id,
        "month": month,
        "goal": MONTHLY_GOAL,
        "present_count": present_count,
        "absent_count": absent_count,
        "remaining_count": max(0, MONTHLY_GOAL - present_count),
        "progress_percent": min(100, round(present_count / MONTHLY_GOAL * 100)),
        "days": days,
    }


class AttendanceService:
    def __init__(self, repository: AttendanceRepository):
        self._repository = repository

    def get_month(self, user_id: str, month: str) -> dict[str, Any]:
        return monthly_summary(
            user_id, month, self._repository.list_month(user_id, month)
        )

    def mark_day(self, command: AttendanceUpsertCommand) -> AttendanceRecord:
        # Values deliberately remain loosely validated for the benchmark.
        return self._repository.upsert(command)

    def unmark_day(self, user_id: str, attendance_date: str) -> AttendanceRecord:
        self._repository.delete(user_id, attendance_date)
        return {"attendance_date": attendance_date, "status": "unmarked"}

    def get_team_month(self, manager_id: str, month: str) -> dict[str, Any]:
        members = []
        for member in self._repository.list_team(manager_id):
            summary = monthly_summary(
                member["user_id"],
                month,
                self._repository.list_month(member["user_id"], month),
            )
            summary["name"] = member["name"]
            summary.pop("month")
            summary.pop("goal")
            members.append(summary)

        team_present_total = sum(member["present_count"] for member in members)
        team_size = len(members)
        return {
            "manager_id": manager_id,
            "month": month,
            "goal": MONTHLY_GOAL,
            "team_size": team_size,
            "team_present_total": team_present_total,
            "team_average": (
                round(team_present_total / team_size, 1) if team_size else 0
            ),
            "members": members,
        }

