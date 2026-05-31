from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ImageUploadResponse(BaseModel):
    id: int
    public_id: str
    secure_url: str
    resource_type: str
    format: str | None
    bytes: int | None
    width: int | None
    height: int | None
    created_at: datetime
    is_deleted: bool
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ImageListResponse(BaseModel):
    items: list[ImageUploadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ImageDeleteResponse(BaseModel):
    id: int
    public_id: str
    cloudinary_result: str
    deleted: bool


class ImageSoftDeleteResponse(BaseModel):
    id: int
    public_id: str
    is_deleted: bool
    deleted_at: datetime | None


class ImageRestoreResponse(BaseModel):
    id: int
    public_id: str
    is_deleted: bool
    deleted_at: datetime | None


class ImageBulkDeleteRequest(BaseModel):
    asset_ids: list[int] = Field(min_length=1)


class ImageBulkDeleteItem(BaseModel):
    id: int
    public_id: str | None = None
    deleted: bool
    cloudinary_result: str | None = None
    error: str | None = None


class ImageBulkDeleteResponse(BaseModel):
    total_requested: int
    total_deleted: int
    total_failed: int
    results: list[ImageBulkDeleteItem]


class DailyUploadStatItem(BaseModel):
    day: date
    upload_count: int


class ImageDashboardStatsResponse(BaseModel):
    range_days: int
    from_date: date
    to_date: date
    total_assets: int
    active_assets: int
    deleted_assets: int
    uploads_by_day: list[DailyUploadStatItem]


class ImageUploadQueuedResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ImageUploadTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    attempts: int
    error: str | None = None
    image_asset_id: int | None = None
    public_id: str | None = None
