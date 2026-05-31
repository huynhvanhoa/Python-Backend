import time

import cloudinary
from app.core.config import settings
from cloudinary import uploader

_is_configured = False


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    keywords = ["slow down", "too many", "rate", "429"]
    return any(keyword in message for keyword in keywords)


def is_rate_limit_error(exc: Exception) -> bool:
    return _is_rate_limit_error(exc)


def configure_cloudinary() -> None:
    global _is_configured
    if _is_configured:
        return

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    _is_configured = True


def upload_image_to_cloudinary(file_stream, filename: str, folder: str) -> dict:
    configure_cloudinary()
    retries = max(1, settings.cloudinary_upload_retries)
    for attempt in range(1, retries + 1):
        try:
            result = uploader.upload(
                file_stream,
                folder=folder,
                resource_type="image",
                use_filename=True,
                unique_filename=True,
                overwrite=False,
                filename=filename,
            )
            break
        except Exception as exc:
            if attempt == retries or not _is_rate_limit_error(exc):
                raise
            delay = settings.cloudinary_retry_base_seconds * (2 ** (attempt - 1))
            time.sleep(delay)
    else:
        raise ValueError("Upload retry loop ended unexpectedly")

    if "public_id" not in result:
        raise ValueError("Cloudinary upload succeeded but public_id is missing")

    return result


def delete_image_from_cloudinary(public_id: str) -> dict:
    configure_cloudinary()
    retries = max(1, settings.cloudinary_upload_retries)
    for attempt in range(1, retries + 1):
        try:
            result = uploader.destroy(public_id, resource_type="image", invalidate=True)
            break
        except Exception as exc:
            if attempt == retries or not _is_rate_limit_error(exc):
                raise
            delay = settings.cloudinary_retry_base_seconds * (2 ** (attempt - 1))
            time.sleep(delay)
    else:
        raise ValueError("Delete retry loop ended unexpectedly")

    if result.get("result") not in {"ok", "not found"}:
        raise ValueError(f"Cloudinary delete failed: {result}")

    return result
