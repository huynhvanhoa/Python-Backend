import io
import json
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import ImageAsset
from app.services.cloudinary_service import (
    is_rate_limit_error,
    upload_image_to_cloudinary,
)
from sqlalchemy.exc import IntegrityError


@dataclass
class UploadTaskState:
    task_id: str
    status: str
    attempts: int
    error: str | None = None
    image_asset_id: int | None = None
    public_id: str | None = None


_task_lock = threading.Lock()
_project_root = Path(__file__).resolve().parents[2]
_task_dir = (_project_root / ".upload_tasks").resolve()


def _ensure_task_dir() -> None:
    _task_dir.mkdir(parents=True, exist_ok=True)


def _task_file(task_id: str) -> Path:
    return _task_dir / f"{task_id}.json"


def _write_task_state(state: UploadTaskState) -> None:
    _ensure_task_dir()
    payload = {
        "task_id": state.task_id,
        "status": state.status,
        "attempts": state.attempts,
        "error": state.error,
        "image_asset_id": state.image_asset_id,
        "public_id": state.public_id,
    }
    _task_file(state.task_id).write_text(json.dumps(payload), encoding="utf-8")


def _read_task_state(task_id: str) -> UploadTaskState | None:
    path = _task_file(task_id)
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return UploadTaskState(**payload)


def enqueue_upload_task(file_bytes: bytes, filename: str, folder: str) -> str:
    task_id = str(uuid.uuid4())

    _ensure_task_dir()
    spool_file = _task_dir / f"{task_id}.bin"
    spool_file.write_bytes(file_bytes)

    with _task_lock:
        state = UploadTaskState(
            task_id=task_id,
            status="queued",
            attempts=0,
        )
        _write_task_state(state)

    thread = threading.Thread(
        target=_run_upload_task,
        args=(task_id, filename, folder),
        daemon=True,
    )
    thread.start()

    return task_id


def get_upload_task(task_id: str) -> UploadTaskState | None:
    with _task_lock:
        state = _read_task_state(task_id)
        if state is None:
            return None
        return UploadTaskState(**state.__dict__)


def _update_task(task_id: str, **fields) -> None:
    with _task_lock:
        state = _read_task_state(task_id)
        if not state:
            return
        for key, value in fields.items():
            setattr(state, key, value)
        _write_task_state(state)


def _run_upload_task(task_id: str, filename: str, folder: str) -> None:
    max_attempts = max(1, settings.upload_queue_retry_attempts)
    base_delay = max(0.5, settings.upload_queue_retry_delay_seconds)
    backoff = max(1.0, settings.upload_queue_retry_backoff_multiplier)
    max_delay = max(base_delay, settings.upload_queue_retry_max_delay_seconds)
    jitter = max(0.0, settings.upload_queue_retry_jitter_seconds)
    spool_file = _task_dir / f"{task_id}.bin"

    if not spool_file.exists():
        _update_task(task_id, status="failed", error="spooled file not found")
        return

    for attempt in range(1, max_attempts + 1):
        _update_task(task_id, status="processing", attempts=attempt, error=None)
        try:
            file_bytes = spool_file.read_bytes()
            upload_result = upload_image_to_cloudinary(
                file_stream=io.BytesIO(file_bytes),
                filename=filename,
                folder=folder,
            )

            db = SessionLocal()
            try:
                asset = ImageAsset(
                    public_id=upload_result["public_id"],
                    secure_url=upload_result.get("secure_url", ""),
                    resource_type=upload_result.get("resource_type", "image"),
                    format=upload_result.get("format"),
                    bytes=upload_result.get("bytes"),
                    width=upload_result.get("width"),
                    height=upload_result.get("height"),
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
            except IntegrityError:
                db.rollback()
                _update_task(
                    task_id,
                    status="failed",
                    error="public_id already exists in database",
                )
                return
            finally:
                db.close()

            _update_task(
                task_id,
                status="succeeded",
                image_asset_id=asset.id,
                public_id=asset.public_id,
            )
            _safe_remove_file(spool_file)
            return
        except Exception as exc:
            if attempt < max_attempts and is_rate_limit_error(exc):
                delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
                if jitter > 0:
                    delay += random.uniform(0, jitter)
                _update_task(
                    task_id,
                    status="retrying",
                    attempts=attempt,
                    error=f"{exc} | next_retry_in={delay:.2f}s",
                )
                time.sleep(delay)
                continue

            _update_task(task_id, status="failed", attempts=attempt, error=str(exc))
            _safe_remove_file(spool_file)
            return


def _safe_remove_file(path: Path) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
