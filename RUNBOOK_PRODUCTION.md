# Production Runbook (Short)

## 0. Quick 60s Release Checklist

Run from project folder:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"

# 1) Sanity check .env
$dbLine = Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $dbLine -or $dbLine -like '*ROTATE_NEON_PASSWORD_NOW*') { throw 'DATABASE_URL is not ready' }

# 2) Migrate
.\.venv\Scripts\python.exe -m alembic upgrade head

# 3) Start API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Smoke test in a second terminal:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
$key = ((Get-Content .env | Where-Object { $_ -match '^ADMIN_API_KEY=' } | Select-Object -First 1).Split('=',2)[1]).Trim('"',"`r","`n")
curl.exe -s http://127.0.0.1:8000/health
curl.exe -s -i "http://127.0.0.1:8000/api/v1/admin/images?page=1&page_size=1&include_deleted=true" -H "X-Admin-Api-Key: $key"
```

Expected:

1. Health response is `{\"status\":\"ok\"}`.
2. Admin list returns `200 OK`.

## 1. Pre-deploy checks

1. Confirm `.env` has valid values:
   - `DATABASE_URL` uses PostgreSQL (`postgresql+psycopg://...`) with SSL.
   - `ALLOW_INSECURE_ADMIN=false`.
   - `ADMIN_API_KEY` is set and strong.
   - Cloudinary keys are present (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`).
2. Ensure no placeholder values remain (for example `ROTATE_NEON_PASSWORD_NOW`).
3. Make sure old leaked secrets are rotated before deploying.

## 2. Deploy steps

From project folder `Python Backend/`:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Smoke tests

```powershell
curl.exe -s http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`

Admin list check:

```powershell
$key = ((Get-Content .env | Where-Object { $_ -match '^ADMIN_API_KEY=' } | Select-Object -First 1).Split('=',2)[1]).Trim('"',"`r","`n")
curl.exe -s -i "http://127.0.0.1:8000/api/v1/admin/images?page=1&page_size=5&include_deleted=true" -H "X-Admin-Api-Key: $key"
```

Expected: `200 OK`.

## 4. Upload flow check (optional but recommended)

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/admin/images/upload" -H "X-Admin-Api-Key: $key" -F "file=@test-upload.png" -F "folder=admin/prod-check"
```

Expected: `201` (or `202` queued when Cloudinary throttles).

## 5. Secret rotation procedure

1. Rotate Neon DB password in Neon Console (`Connect` -> `Reset password`).
2. Rotate Cloudinary API secret in Cloudinary Console.
3. Update `.env` values.
4. Restart backend process.
5. Re-run smoke tests.

## 6. Incident quick actions

1. If admin endpoints return `401` unexpectedly:
   - Verify `ADMIN_API_KEY` header and `.env` key match.
   - Restart process to reload `.env`.
2. If startup fails with missing env vars:
   - Confirm `.env` path and required keys.
3. If DB errors occur:
   - Verify `DATABASE_URL` + SSL + network access.
   - Re-run `alembic upgrade head`.
4. If uploads fail with rate-limit:
   - Check queue endpoint `/api/v1/admin/images/upload-tasks/{task_id}`.

## 7. Do not do in production

1. Do not set `ALLOW_INSECURE_ADMIN=true`.
2. Do not commit `.env` or any secrets.
3. Do not expose secret values in docs/screenshots.

## 8. Cloud Deploy (Render)

This repository is ready for Render using:

1. `render.yaml`
2. `scripts/start_render.sh` (runs `alembic upgrade head` before startup)

Deploy steps:

1. Push this project to GitHub.
2. In Render: `New` -> `Blueprint` -> select your repo.
3. Render will detect `render.yaml` and create service `python-backend`.
4. Set required env vars in Render dashboard:
   - `DATABASE_URL`
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `ADMIN_API_KEY`
   - `ALLOW_INSECURE_ADMIN=false`
   - See `RENDER_ENV_CHECKLIST.md` for a copy-paste template.
   - Run `./.venv/Scripts/python.exe scripts/check_env_ready.py` locally before pushing.
5. Deploy.
6. Verify health: `https://<your-render-domain>/health`.
