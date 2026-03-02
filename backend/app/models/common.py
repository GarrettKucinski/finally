"""Common Pydantic models shared across the FinAlly API."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response format for all API errors.

    Used consistently across all endpoints for 400, 404, and 500 responses.
    """

    error: str
    detail: str
