import io
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import enforce_upload_rate_limit, verify_admin_access
from app.db.database import get_db
from app.db.models import ImageAsset
from app.schemas.image import (
    DailyUploadStatItem,
    ImageBulkDeleteItem,
    ImageBulkDeleteRequest,
    ImageBulkDeleteResponse,
    ImageDashboardStatsResponse,
    ImageDeleteResponse,
    ImageListResponse,
    ImageRestoreResponse,
    ImageSoftDeleteResponse,
    ImageUploadQueuedResponse,
    ImageUploadResponse,
    ImageUploadTaskStatusResponse,
)
from app.services.cloudinary_service import (
    delete_image_from_cloudinary,
    is_rate_limit_error,
    upload_image_to_cloudinary,
)
from app.services.upload_queue import enqueue_upload_task, get_upload_task

router = APIRouter(
    prefix="/admin/images",
    tags=["Admin Image Upload"],
    dependencies=[Depends(verify_admin_access)],
)


@router.get("/stats/uploads-by-day", response_model=ImageDashboardStatsResponse)
def get_uploads_by_day_stats(
    days: int = Query(default=30, ge=1, le=365),
    include_deleted: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days - 1)
    from_dt = datetime.combine(from_date, datetime.min.time())

    base_query = db.query(ImageAsset).filter(ImageAsset.created_at >= from_dt)
    if not include_deleted:
        base_query = base_query.filter(ImageAsset.is_deleted.is_(False))

    grouped_rows = (
        base_query.with_entities(
            func.date(ImageAsset.created_at).label("day"),
            func.count(ImageAsset.id).label("upload_count"),
        )
        .group_by(func.date(ImageAsset.created_at))
        .all()
    )

    grouped_map: dict = {}
    for row in grouped_rows:
        day_value = row.day if hasattr(row, "day") else row[0]
        count_value = row.upload_count if hasattr(row, "upload_count") else row[1]
        if isinstance(day_value, str):
            normalized_day = datetime.strptime(day_value, "%Y-%m-%d").date()
        else:
            normalized_day = day_value
        grouped_map[normalized_day] = int(count_value)

    uploads_by_day: list[DailyUploadStatItem] = []
    for i in range(days):
        current_day = from_date + timedelta(days=i)
        uploads_by_day.append(
            DailyUploadStatItem(
                day=current_day,
                upload_count=grouped_map.get(current_day, 0),
            )
        )

    total_assets = db.query(ImageAsset).count()
    deleted_assets = (
        db.query(ImageAsset).filter(ImageAsset.is_deleted.is_(True)).count()
    )
    active_assets = total_assets - deleted_assets

    return ImageDashboardStatsResponse(
        range_days=days,
        from_date=from_date,
        to_date=to_date,
        total_assets=total_assets,
        active_assets=active_assets,
        deleted_assets=deleted_assets,
        uploads_by_day=uploads_by_day,
    )


@router.get("", response_model=ImageListResponse)
def list_uploaded_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_deleted: bool = Query(default=False),
    public_id_keyword: str | None = Query(default=None),
    folder: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="created_from must be less than or equal to created_to",
        )

    offset = (page - 1) * page_size

    base_query = db.query(ImageAsset)
    if not include_deleted:
        base_query = base_query.filter(ImageAsset.is_deleted.is_(False))

    if public_id_keyword:
        base_query = base_query.filter(
            ImageAsset.public_id.ilike(f"%{public_id_keyword}%")
        )

    if folder:
        normalized_folder = folder.strip("/")
        if normalized_folder:
            base_query = base_query.filter(
                ImageAsset.public_id.ilike(f"{normalized_folder}/%")
            )

    if created_from:
        base_query = base_query.filter(ImageAsset.created_at >= created_from)

    if created_to:
        base_query = base_query.filter(ImageAsset.created_at <= created_to)

    total = base_query.count()
    items = (
        base_query.order_by(ImageAsset.created_at.desc(), ImageAsset.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return ImageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.options("/upload")
async def upload_options():
    """Handle CORS preflight for file uploads."""
    origin = ", ".join(settings.backend_cors_origins) if settings.backend_cors_origins != ["*"] else "*"
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(settings.cors_allow_methods),
            "Access-Control-Allow-Headers": ", ".join(settings.cors_allow_headers),
            "Access-Control-Max-Age": "600",
        },
    )



@router.post(
    "/upload",
    response_model=ImageUploadResponse | ImageUploadQueuedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_upload_rate_limit)],
)
async def upload_admin_image(
    file: UploadFile = File(...),
    folder: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    target_folder = folder or settings.cloudinary_folder
    file_bytes = await file.read()
    filename = file.filename or "uploaded-image"

    try:
        upload_result = upload_image_to_cloudinary(
            file_stream=io.BytesIO(file_bytes),
            filename=filename,
            folder=target_folder,
        )
    except Exception as exc:
        error_text = str(exc).lower()
        throttled = is_rate_limit_error(exc) or any(
            token in error_text
            for token in ("slow down", "too many", "429", "rate limit")
        )

        if throttled:
            task_id = enqueue_upload_task(
                file_bytes=file_bytes,
                filename=filename,
                folder=target_folder,
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=ImageUploadQueuedResponse(
                    task_id=task_id,
                    status="queued",
                    message="Upload queued due to Cloudinary rate limit",
                ).model_dump(),
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload to Cloudinary failed: {exc}",
        ) from exc
    finally:
        await file.close()

    asset = ImageAsset(
        public_id=upload_result["public_id"],
        secure_url=upload_result.get("secure_url", ""),
        resource_type=upload_result.get("resource_type", "image"),
        format=upload_result.get("format"),
        bytes=upload_result.get("bytes"),
        width=upload_result.get("width"),
        height=upload_result.get("height"),
    )

    try:
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="public_id already exists in database",
        ) from exc

    return asset


            "Access-Control-Allow-Headers": ",".join(settings.cors_allow_headers),
        },
    )


@router.get("/upload-tasks/{task_id}", response_model=ImageUploadTaskStatusResponse)
def get_upload_task_status(task_id: str):
    task = get_upload_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload task not found",
        )

    return ImageUploadTaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        attempts=task.attempts,
        error=task.error,
        image_asset_id=task.image_asset_id,
        public_id=task.public_id,
    )


@router.get("/{asset_id}", response_model=ImageUploadResponse)
def get_uploaded_image(
    asset_id: int,
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = db.query(ImageAsset).filter(ImageAsset.id == asset_id)
    if not include_deleted:
        query = query.filter(ImageAsset.is_deleted.is_(False))
    asset = query.first()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image asset not found",
        )
    return asset


@router.patch("/{asset_id}/soft-delete", response_model=ImageSoftDeleteResponse)
def soft_delete_uploaded_image(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image asset not found",
        )

    if not asset.is_deleted:
        asset.is_deleted = True
        asset.deleted_at = datetime.utcnow()
        db.commit()
        db.refresh(asset)

    return ImageSoftDeleteResponse(
        id=asset.id,
        public_id=asset.public_id,
        is_deleted=asset.is_deleted,
        deleted_at=asset.deleted_at,
    )


@router.patch("/{asset_id}/restore", response_model=ImageRestoreResponse)
def restore_uploaded_image(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image asset not found",
        )

    if asset.is_deleted:
        asset.is_deleted = False
        asset.deleted_at = None
        db.commit()
        db.refresh(asset)

    return ImageRestoreResponse(
        id=asset.id,
        public_id=asset.public_id,
        is_deleted=asset.is_deleted,
        deleted_at=asset.deleted_at,
    )


@router.delete("/{asset_id}", response_model=ImageDeleteResponse)
def delete_uploaded_image(
    asset_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image asset not found",
        )

    if not force and not asset.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Image must be soft-deleted before hard delete. Use force=true to bypass.",
        )

    try:
        delete_result = delete_image_from_cloudinary(asset.public_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Delete from Cloudinary failed: {exc}",
        ) from exc

    db.delete(asset)
    db.commit()

    return ImageDeleteResponse(
        id=asset_id,
        public_id=asset.public_id,
        cloudinary_result=delete_result.get("result", "unknown"),
        deleted=True,
    )




@router.post("/bulk-delete", response_model=ImageBulkDeleteResponse)
def bulk_delete_uploaded_images(
    payload: ImageBulkDeleteRequest = Body(...),
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    requested_ids: list[int] = list(dict.fromkeys(payload.asset_ids))

    assets = db.query(ImageAsset).filter(ImageAsset.id.in_(requested_ids)).all()
    asset_by_id = {asset.id: asset for asset in assets}

    results: list[ImageBulkDeleteItem] = []
    deleted_count = 0

    for asset_id in requested_ids:
        asset = asset_by_id.get(asset_id)
        if asset is None:
            results.append(
                ImageBulkDeleteItem(
                    id=asset_id,
                    deleted=False,
                    error="Image asset not found",
                )
            )
            continue

        if not force and not asset.is_deleted:
            results.append(
                ImageBulkDeleteItem(
                    id=asset_id,
                    public_id=asset.public_id,
                    deleted=False,
                    error="Image must be soft-deleted before hard delete. Use force=true to bypass.",
                )
            )
            continue

        try:
            delete_result = delete_image_from_cloudinary(asset.public_id)
            db.delete(asset)
            deleted_count += 1
            results.append(
                ImageBulkDeleteItem(
                    id=asset_id,
                    public_id=asset.public_id,
                    deleted=True,
                    cloudinary_result=delete_result.get("result", "unknown"),
                )
            )
        except Exception as exc:
            results.append(
                ImageBulkDeleteItem(
                    id=asset_id,
                    public_id=asset.public_id,
                    deleted=False,
                    error=f"Delete from Cloudinary failed: {exc}",
                )
            )

    if deleted_count > 0:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database commit failed after bulk delete: {exc}",
            ) from exc

    failed_count = len(results) - deleted_count
    return ImageBulkDeleteResponse(
        total_requested=len(requested_ids),
        total_deleted=deleted_count,
        total_failed=failed_count,
        results=results,
    )




