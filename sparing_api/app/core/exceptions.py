"""
Custom exceptions for API error handling.
Provides consistent error response format across all endpoints.
"""
from fastapi import HTTPException
from typing import Any, Optional


class APIError(Exception):
    """Base API error with structured response format."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        response = {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} tidak ditemukan"
        if identifier:
            message = f"{resource} '{identifier}' tidak ditemukan"
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=404
        )


class ValidationError(APIError):
    """Data validation error."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details
        )


class AuthenticationError(APIError):
    """Authentication failed error."""
    
    def __init__(self, message: str = "Autentikasi gagal"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401
        )


class ForbiddenError(APIError):
    """Access forbidden error."""
    
    def __init__(self, message: str = "Akses ditolak"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(self):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Terlalu banyak request. Silakan coba lagi nanti.",
            status_code=429
        )


class ConflictError(APIError):
    """Resource conflict error (e.g., duplicate)."""
    
    def __init__(self, message: str):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409
        )


class InternalServerError(APIError):
    """Internal server error."""
    
    def __init__(self, message: str = "Terjadi kesalahan server"):
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            status_code=500
        )
