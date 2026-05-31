import threading
import time
from collections import defaultdict, deque

from app.core.config import settings
from fastapi import Header, HTTPException, Request, status

_upload_rate_lock = threading.Lock()
_upload_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def verify_admin_access(x_admin_api_key: str | None = Header(default=None)) -> None:
    if settings.allow_insecure_admin:
        return

    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured",
        )

    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )


def enforce_upload_rate_limit(request: Request) -> None:
    max_requests = max(1, settings.upload_rate_limit_max_requests)
    window_seconds = max(1, settings.upload_rate_limit_window_seconds)

    client_host = request.client.host if request.client else "unknown"
    now = time.time()
    threshold = now - window_seconds

    with _upload_rate_lock:
        bucket = _upload_rate_buckets[client_host]
        while bucket and bucket[0] < threshold:
            bucket.popleft()

        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many upload requests. Please try again later.",
            )

        bucket.append(now)
