from app.domain.errors import DailyCapacityReached, MissingRequiredFields, VisitNotFound
from app.domain.models import VisitCreateCommand, VisitUpdateCommand
from app.domain.ports import VisitRecord, VisitRepository


class VisitService:
    def __init__(self, repository: VisitRepository):
        self._repository = repository

    def list_visits(self, user_id: str, query: str = "") -> list[VisitRecord]:
        return self._repository.list(user_id, query)

    def create_visit(self, command: VisitCreateCommand) -> VisitRecord:
        if (
            not command.user_id
            or not command.visitor_name
            or not command.visit_date
            or not command.start_time
        ):
            raise MissingRequiredFields
        if self._repository.count_scheduled_on(command.visit_date) >= 5:
            raise DailyCapacityReached
        return self._repository.create(command)

    def update_visit(
        self, visit_id: int, command: VisitUpdateCommand
    ) -> VisitRecord:
        if self._repository.get(visit_id) is None:
            raise VisitNotFound
        return self._repository.update(visit_id, command)

    def cancel_visit(self, visit_id: int) -> VisitRecord:
        if self._repository.get(visit_id) is None:
            raise VisitNotFound
        self._repository.cancel(visit_id)
        return {"id": visit_id, "status": "cancelled"}

    def summarize(self, user_id: str) -> VisitRecord:
        return self._repository.summarize(user_id)
