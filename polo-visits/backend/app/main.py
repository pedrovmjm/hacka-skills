from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.http.api import create_router
from app.adapters.persistence.sqlite import SQLiteAttendanceRepository, connection
from app.application.attendance_service import AttendanceService


app = FastAPI(title="Presença no Polo", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = SQLiteAttendanceRepository(connection)
service = AttendanceService(repository)
app.include_router(create_router(service))
