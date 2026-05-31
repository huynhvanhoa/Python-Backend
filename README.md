# Python Backend - Upload Admin Image to Cloudinary

Backend nay nhan file anh tu trang quan tri, upload len Cloudinary, lay `public_id` va luu metadata vao database.

Database migration duoc quan ly bang Alembic (khong dung `create_all` tu dong).

## 1. Cai dat

```bash
pip install -r requirements.txt
```

## 2. Cau hinh bien moi truong

Tao file `.env` tu `.env.example` va cap nhat:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `DATABASE_URL` (mac dinh PostgreSQL)
- `ADMIN_API_KEY` (bat buoc cho production)
- `ALLOW_INSECURE_ADMIN` (`false` cho production, `true` chi de local)

Vi du:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/python_backend
ADMIN_API_KEY=replace_with_strong_random_secret
ALLOW_INSECURE_ADMIN=false
UPLOAD_RATE_LIMIT_MAX_REQUESTS=10
UPLOAD_RATE_LIMIT_WINDOW_SECONDS=60
LOG_LEVEL=INFO
```

Khi `ALLOW_INSECURE_ADMIN=false`, tat ca endpoint admin can header:

```http
X-Admin-Api-Key: <ADMIN_API_KEY>
```

## 3. Chay migration

```bash
alembic upgrade head
```

## 4. Chay ung dung

```bash
uvicorn app.main:app --reload
```

## 5. API upload anh

- Method: `POST`
- URL: `/api/v1/admin/images/upload`
- Content-Type: `multipart/form-data`
- Fields:
  - `file`: image file (required)
  - `folder`: Cloudinary folder (optional, mac dinh tu `CLOUDINARY_FOLDER`)

### Curl test

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/images/upload" \
  -H "accept: application/json" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/image.jpg" \
  -F "folder=admin/products"
```

### Response mau

```json
{
  "id": 1,
  "public_id": "admin/products/image_xxxxx",
  "secure_url": "https://res.cloudinary.com/...",
  "resource_type": "image",
  "format": "jpg",
  "bytes": 123456,
  "width": 1200,
  "height": 800,
  "created_at": "2026-05-30T12:00:00"
}
```

Neu Cloudinary bi throttle (rate-limit), endpoint se tra `202 Accepted` va dua upload vao queue nen:

```json
{
  "task_id": "3f7d0b62-9b6d-4bd0-b98a-3f9d8475ad20",
  "status": "queued",
  "message": "Upload queued due to Cloudinary rate limit"
}
```

Kiem tra trang thai job upload nen:

- Method: `GET`
- URL: `/api/v1/admin/images/upload-tasks/{task_id}`

Trang thai co the la: `queued`, `processing`, `retrying`, `succeeded`, `failed`.

Queue retry su dung exponential backoff + jitter de giam kha nang bi throttle lap lai.
Co the chinh qua bien moi truong:

- `UPLOAD_QUEUE_RETRY_ATTEMPTS`
- `UPLOAD_QUEUE_RETRY_DELAY_SECONDS`
- `UPLOAD_QUEUE_RETRY_BACKOFF_MULTIPLIER`
- `UPLOAD_QUEUE_RETRY_MAX_DELAY_SECONDS`
- `UPLOAD_QUEUE_RETRY_JITTER_SECONDS`

## 6. API lay danh sach anh da upload (phan trang)

- Method: `GET`
- URL: `/api/v1/admin/images?page=1&page_size=20`
- Query params:
  - `page` (mac dinh `1`)
  - `page_size` (mac dinh `20`, toi da `100`)
  - `include_deleted` (mac dinh `false`)
  - `public_id_keyword` (tim theo chuoi trong `public_id`)
  - `folder` (loc theo thu muc Cloudinary, vd `admin/products`)
  - `created_from` (ISO datetime)
  - `created_to` (ISO datetime)

### Vi du loc

```bash
curl -G "http://127.0.0.1:8000/api/v1/admin/images" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=20" \
  --data-urlencode "include_deleted=true" \
  --data-urlencode "public_id_keyword=summer" \
  --data-urlencode "folder=admin/products" \
  --data-urlencode "created_from=2026-05-01T00:00:00" \
  --data-urlencode "created_to=2026-05-31T23:59:59"
```

### Response mau

```json
{
  "items": [
    {
      "id": 1,
      "public_id": "admin/products/image_xxxxx",
      "secure_url": "https://res.cloudinary.com/...",
      "resource_type": "image",
      "format": "jpg",
      "bytes": 123456,
      "width": 1200,
      "height": 800,
      "created_at": "2026-05-30T12:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

## 7. API lay chi tiet 1 anh

- Method: `GET`
- URL: `/api/v1/admin/images/{asset_id}`
- Query params:
  - `include_deleted` (mac dinh `false`)

### Curl test

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/admin/images/1" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -H "accept: application/json"
```

## 8. API soft delete (danh dau da xoa)

- Method: `PATCH`
- URL: `/api/v1/admin/images/{asset_id}/soft-delete`

### Curl test

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/admin/images/1/soft-delete" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -H "accept: application/json"
```

## 9. API restore (hoan tac soft delete)

- Method: `PATCH`
- URL: `/api/v1/admin/images/{asset_id}/restore`

### Curl test

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/admin/images/1/restore" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -H "accept: application/json"
```

## 10. Luu y khi tich hop frontend quan tri

Trang quan tri chi can gui `multipart/form-data` den endpoint tren. Backend se:

1. Kiem tra file co phai image.
2. Upload len Cloudinary.
3. Lay `public_id` + metadata.
4. Luu vao bang `image_assets`.
5. Tra ve JSON cho frontend su dung.

## 11. API xoa anh (hard delete: xoa Cloudinary + DB)

- Method: `DELETE`
- URL: `/api/v1/admin/images/{asset_id}`
- Query params:
  - `force` (mac dinh `false`)

Mac dinh API yeu cau anh da duoc soft delete truoc. Neu muon bo qua buoc nay, truyen `force=true`.

### Curl test

```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/admin/images/1?force=true" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -H "accept: application/json"
```

### Response mau

```json
{
  "id": 1,
  "public_id": "admin/products/image_xxxxx",
  "cloudinary_result": "ok",
  "deleted": true
}
```

## 12. API xoa nhieu anh (bulk hard delete)

- Method: `POST`
- URL: `/api/v1/admin/images/bulk-delete`
- Query params:
  - `force` (mac dinh `false`)
- Body:

```json
{
  "asset_ids": [1, 2, 3]
}
```

### Response mau

```json
{
  "total_requested": 3,
  "total_deleted": 2,
  "total_failed": 1,
  "results": [
    {
      "id": 1,
      "public_id": "admin/products/image_a",
      "deleted": true,
      "cloudinary_result": "ok",
      "error": null
    },
    {
      "id": 2,
      "public_id": "admin/products/image_b",
      "deleted": true,
      "cloudinary_result": "not found",
      "error": null
    },
    {
      "id": 3,
      "public_id": null,
      "deleted": false,
      "cloudinary_result": null,
      "error": "Image asset not found"
    }
  ]
}
```

## 13. API thong ke dashboard (upload theo ngay)

- Method: `GET`
- URL: `/api/v1/admin/images/stats/uploads-by-day`
- Query params:
  - `days` (mac dinh `30`, tu `1` den `365`)
  - `include_deleted` (mac dinh `true`)

### Curl test

```bash
curl -G "http://127.0.0.1:8000/api/v1/admin/images/stats/uploads-by-day" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  --data-urlencode "days=30" \
  --data-urlencode "include_deleted=true"
```

### Response mau

```json
{
  "range_days": 30,
  "from_date": "2026-05-01",
  "to_date": "2026-05-30",
  "total_assets": 120,
  "active_assets": 110,
  "deleted_assets": 10,
  "uploads_by_day": [
    { "day": "2026-05-01", "upload_count": 2 },
    { "day": "2026-05-02", "upload_count": 0 },
    { "day": "2026-05-03", "upload_count": 5 }
  ]
}
```

## 14. Tao migration moi (khi doi schema)

```bash
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

## 15. Ghi chu ve created_at

Cot `created_at` da duoc dat `server_default=now()` o PostgreSQL qua migration,
nen insert truc tiep vao DB van co timestamp ngay ca khi khong qua ung dung.

## 16. Ghi chu ve soft delete

- Sau khi chay migration moi, bang `image_assets` co them:
  - `is_deleted` (bool)
  - `deleted_at` (datetime, nullable)
- List/Get mac dinh an ban ghi da soft delete. De xem ca ban ghi da xoa, dung `include_deleted=true`.

## 17. Production checklist

- Dat `ALLOW_INSECURE_ADMIN=false` va cau hinh `ADMIN_API_KEY` manh.
- Dat gioi han upload theo IP bang `UPLOAD_RATE_LIMIT_MAX_REQUESTS` va `UPLOAD_RATE_LIMIT_WINDOW_SECONDS`.
- Theo doi `X-Request-ID` trong response de truy vet log theo request.
- Khong commit file `.env` len git.
- Rotate Cloudinary API Secret neu da tung chia se trong log/chat.
- Dung PostgreSQL cho production, khong dung SQLite.
- Dat reverse proxy va HTTPS truoc API.
