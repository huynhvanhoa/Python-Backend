import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.upload import router as upload_router
from app.core.config import settings
from app.core.logging_config import attach_request_id_filter, configure_logging

configure_logging()
attach_request_id_filter()

access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.error")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


@app.middleware("http")
async def request_id_and_access_log_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except HTTPException:
        raise
    except RequestValidationError:
        raise
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        error_logger.exception(
            "request_failed method=%s path=%s client_ip=%s status=%s latency_ms=%.2f error=%s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
            500,
            latency_ms,
            exc,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    latency_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id

    access_logger.info(
        "request_completed method=%s path=%s client_ip=%s status=%s latency_ms=%.2f",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
        response.status_code,
        latency_ms,
        extra={"request_id": request_id},
    )

    return response


app.include_router(upload_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}
