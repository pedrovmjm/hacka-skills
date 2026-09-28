from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import database


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


app = FastAPI(title="Idas ao Polo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/visits")
async def list_visits(
    user_id: str = Query(...),
    q: str = Query(""),
    x_user: str = Header(..., alias="X-User"),
):
    if q:
        sql = (
            "SELECT * FROM visits "
            f"WHERE user_id = '{user_id}' AND purpose LIKE '%{q}%' "
            f"OR notes LIKE '%{q}%' ORDER BY visit_date, start_time"
        )
        rows = database.connection.execute(sql).fetchall()
    else:
        rows = database.connection.execute(
            "SELECT * FROM visits WHERE user_id = ? ORDER BY visit_date, start_time",
            (user_id,),
        ).fetchall()
    return [database.row_to_dict(row) for row in rows]


@app.post("/api/visits", status_code=201)
async def create_visit(body: VisitCreate, x_user: str = Header(..., alias="X-User")):
    if not body.user_id or not body.visitor_name or not body.visit_date or not body.start_time:
        raise HTTPException(status_code=400, detail="Campos obrigatorios ausentes")
    occupied = database.connection.execute(
        "SELECT COUNT(*) AS total FROM visits WHERE visit_date = ? AND status = 'scheduled'",
        (body.visit_date,),
    ).fetchone()["total"]
    if occupied >= 5:
        raise HTTPException(status_code=409, detail="Capacidade diaria atingida")
    now = database.timestamp()
    cursor = database.connection.execute(
        """
        INSERT INTO visits
            (user_id, visitor_name, visit_date, start_time, purpose, notes,
             companions, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
        """,
        (
            body.user_id,
            body.visitor_name,
            body.visit_date,
            body.start_time,
            body.purpose,
            body.notes,
            body.companions,
            now,
            now,
        ),
    )
    database.connection.commit()
    row = database.connection.execute(
        "SELECT * FROM visits WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return database.row_to_dict(row)


@app.put("/api/visits/{visit_id}")
async def update_visit(
    visit_id: int,
    body: VisitUpdate,
    x_user: str = Header(..., alias="X-User"),
):
    current = database.connection.execute(
        "SELECT * FROM visits WHERE id = ?", (visit_id,)
    ).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Visita nao encontrada")
    database.connection.execute(
        """
        UPDATE visits
        SET visitor_name = ?, visit_date = ?, start_time = ?, purpose = ?,
            notes = ?, companions = ?, status = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            body.visitor_name,
            body.visit_date,
            body.start_time,
            body.purpose,
            body.notes,
            body.companions,
            body.status,
            database.timestamp(),
            visit_id,
        ),
    )
    database.connection.commit()
    changed = database.connection.execute(
        "SELECT * FROM visits WHERE id = ?", (visit_id,)
    ).fetchone()
    return database.row_to_dict(changed)


@app.delete("/api/visits/{visit_id}")
async def cancel_visit(visit_id: int, x_user: str = Header(..., alias="X-User")):
    current = database.connection.execute(
        "SELECT * FROM visits WHERE id = ?", (visit_id,)
    ).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Visita nao encontrada")
    database.connection.execute(
        "UPDATE visits SET status = 'cancelled', updated_at = ? WHERE id = ?",
        (database.timestamp(), visit_id),
    )
    database.connection.commit()
    return {"id": visit_id, "status": "cancelled"}


@app.get("/api/summary")
async def summary(user_id: str, x_user: str = Header(..., alias="X-User")):
    rows = database.connection.execute(
        "SELECT status, COUNT(*) AS total FROM visits WHERE user_id = ? GROUP BY status",
        (user_id,),
    ).fetchall()
    totals: dict[str, Any] = {"scheduled": 0, "completed": 0, "cancelled": 0}
    for row in rows:
        totals[row["status"]] = row["total"]
    totals["total"] = sum(row["total"] for row in rows)
    totals["user_id"] = user_id
    return totals

