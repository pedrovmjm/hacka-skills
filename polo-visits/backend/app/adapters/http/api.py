from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.application.visit_service import VisitService
from app.domain.errors import DailyCapacityReached, MissingRequiredFields, VisitNotFound
from app.domain.models import VisitCreateCommand, VisitUpdateCommand


class VisitCreate(BaseModel):
    user_id: str
    visitor_name: str
    visit_date: str
    start_time: str
    purpose: str
    notes: str = ""
    companions: int = 0


class VisitUpdate(BaseModel):
    visitor_name: str
    visit_date: str
    start_time: str
    purpose: str
    notes: str = ""
    companions: int = 0
    status: str = "scheduled"


def create_router(service: VisitService) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/api/visits")
    async def list_visits(
        user_id: str = Query(...),
        q: str = Query(""),
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.list_visits(user_id, q)

    @router.post("/api/visits", status_code=201)
    async def create_visit(
        body: VisitCreate,
        x_user: str = Header(..., alias="X-User"),
    ):
        command = VisitCreateCommand(**body.model_dump())
        try:
            return service.create_visit(command)
        except MissingRequiredFields as error:
            raise HTTPException(
                status_code=400, detail="Campos obrigatorios ausentes"
            ) from error
        except DailyCapacityReached as error:
            raise HTTPException(
                status_code=409, detail="Capacidade diaria atingida"
            ) from error

    @router.put("/api/visits/{visit_id}")
    async def update_visit(
        visit_id: int,
        body: VisitUpdate,
        x_user: str = Header(..., alias="X-User"),
    ):
        try:
            return service.update_visit(
                visit_id, VisitUpdateCommand(**body.model_dump())
            )
        except VisitNotFound as error:
            raise HTTPException(status_code=404, detail="Visita nao encontrada") from error

    @router.delete("/api/visits/{visit_id}")
    async def cancel_visit(
        visit_id: int,
        x_user: str = Header(..., alias="X-User"),
    ):
        try:
            return service.cancel_visit(visit_id)
        except VisitNotFound as error:
            raise HTTPException(status_code=404, detail="Visita nao encontrada") from error

    @router.get("/api/summary")
    async def summary(
        user_id: str,
        x_user: str = Header(..., alias="X-User"),
    ):
        return service.summarize(user_id)

    return router
