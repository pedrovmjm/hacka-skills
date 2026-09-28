from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from app.application.attendance_service import AttendanceService
from app.domain.models import AttendanceUpsertCommand


class AttendanceUpsert(BaseModel):
    user_id: str
    status: str
    notes: str = ""


def create_router(service: AttendanceService) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/api/attendance")
    async def attendance(
        user_id: str = Query(...),
        month: str = Query(...),
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.get_month(user_id, month)

    @router.put("/api/attendance/{attendance_date}")
    async def mark_attendance(
        attendance_date: str,
        body: AttendanceUpsert,
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.mark_day(
            AttendanceUpsertCommand(
                user_id=body.user_id,
                attendance_date=attendance_date,
                status=body.status,
                notes=body.notes,
            )
        )

    @router.delete("/api/attendance/{attendance_date}")
    async def unmark_attendance(
        attendance_date: str,
        user_id: str = Query(...),
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.unmark_day(user_id, attendance_date)

    @router.get("/api/team-attendance")
    async def team_attendance(
        manager_id: str = Query(...),
        month: str = Query(...),
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.get_team_month(manager_id, month)

    return router
