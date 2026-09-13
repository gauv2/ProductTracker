"""Standard error shape, per docs/api-contract.md's "Errors" section."""

from __future__ import annotations


class ApiError(Exception):
    status_code: int
    code: str

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ValidationErrorApi(ApiError):
    status_code = 422
    code = "validation_error"


class UpstreamUnavailableError(ApiError):
    status_code = 502
    code = "upstream_unavailable"


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
