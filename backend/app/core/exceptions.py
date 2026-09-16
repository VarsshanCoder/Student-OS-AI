from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class ScholarOSError(Exception):
    """Base exception for all ScholarOS custom errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(self.message)

class NotFoundError(ScholarOSError):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, code="NOT_FOUND")

class AuthorizationError(ScholarOSError):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, code="AUTHORIZATION_ERROR")

class ValidationError(ScholarOSError):
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, code="VALIDATION_ERROR")

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(ScholarOSError)
    async def scholaros_error_handler(request: Request, exc: ScholarOSError):
        logger.error(f"ScholarOSError [{exc.code}]: {exc.message}")
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        req_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "request_id": req_id
                }
            }
        )
