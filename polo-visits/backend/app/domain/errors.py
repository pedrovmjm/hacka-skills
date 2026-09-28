class VisitError(Exception):
    """Base exception for visit use cases."""


class MissingRequiredFields(VisitError):
    pass


class DailyCapacityReached(VisitError):
    pass


class VisitNotFound(VisitError):
    pass
