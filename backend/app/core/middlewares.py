import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store the request ID for logging or deep service access
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")

class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if X-Request-ID is already in headers (e.g., set by Cloudflare)
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        request_id_ctx_var.set(request_id)
        
        # Attach request_id to request state so other parts of the app can use it easily
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)
        
        # Always return the request ID to the client
        response.headers["X-Request-ID"] = request_id
        return response
