from dataclasses import dataclass


MONTHLY_GOAL = 8


@dataclass(frozen=True)
class AttendanceUpsertCommand:
    user_id: str
    attendance_date: str
    status: str
    notes: str = ""
