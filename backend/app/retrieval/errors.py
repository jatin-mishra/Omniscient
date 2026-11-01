from app.errors import AppError


class SearchUnavailableError(AppError):
    status_code = 503
    code = "search_unavailable"
