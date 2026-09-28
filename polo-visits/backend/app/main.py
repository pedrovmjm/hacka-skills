from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.http.api import create_router
from app.adapters.persistence.sqlite import SQLiteVisitRepository, connection
from app.application.visit_service import VisitService


app = FastAPI(title="Idas ao Polo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = SQLiteVisitRepository(connection)
service = VisitService(repository)
app.include_router(create_router(service))
