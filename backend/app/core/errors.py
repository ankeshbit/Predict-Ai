"""
Standardized API error response and custom application exceptions.
Matches PRD and engineering standards:
{"error": {"code": "...", "message": "...", "details": ...}}
"""

from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetails


class AppError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


# Convenience domain exceptions
class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid credentials", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message,
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, code: str = "CONFLICT", message: str = "Resource conflict", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code=code,
            message=message,
            details=details,
        )


class DatasetIncompatibleError(AppError):
    def __init__(self, message: str = "This dataset is not compatible with the selected model.", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="DATASET_INCOMPATIBLE",
            message=message,
            details=details,
        )


class StagingExpiredError(AppError):
    def __init__(self, message: str = "Staging upload has expired. Please re-upload.", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            code="STAGING_EXPIRED",
            message=message,
            details=details,
        )


class BadRequestError(AppError):
    def __init__(self, code: str = "BAD_REQUEST", message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            message=message,
            details=details,
        )


class ValidationError(AppError):
    def __init__(self, code: str = "VALIDATION_ERROR", message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=code,
            message=message,
            details=details,
        )


class InternalServerError(AppError):
    def __init__(self, code: str = "INTERNAL_SERVER_ERROR", message: str = "Internal server error", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=code,
            message=message,
            details=details,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Format pydantic validation errors cleanly
    details = []
    for err in exc.errors():
        loc = " -> ".join([str(part) for part in err.get("loc", [])])
        details.append({"location": loc, "issue": err.get("msg")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak stack trace to clients in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": None,
            }
        },
    )
