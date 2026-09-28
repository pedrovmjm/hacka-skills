from dataclasses import dataclass


@dataclass(frozen=True)
class VisitCreateCommand:
    user_id: str
    visitor_name: str
    visit_date: str
    start_time: str
    purpose: str
    notes: str = ""
    companions: int = 0


@dataclass(frozen=True)
class VisitUpdateCommand:
    visitor_name: str
    visit_date: str
    start_time: str
    purpose: str
    notes: str = ""
    companions: int = 0
    status: str = "scheduled"
