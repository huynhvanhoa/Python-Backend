# Render Environment Checklist

Use these values in Render service Environment tab.

Required variables:

- DATABASE_URL=postgresql+psycopg://<neon_user>:<neon_password>@<neon_host>/<neon_db>?sslmode=require&channel_binding=require
- CLOUDINARY_CLOUD_NAME=<your_cloud_name>
- CLOUDINARY_API_KEY=<your_cloudinary_api_key>
- CLOUDINARY_API_SECRET=<your_cloudinary_api_secret>
- ADMIN_API_KEY=<your_strong_admin_api_key>
- ALLOW_INSECURE_ADMIN=false
- LOG_LEVEL=INFO

Optional (recommended defaults):

- CLOUDINARY_FOLDER=admin_uploads
- CLOUDINARY_UPLOAD_RETRIES=3
- CLOUDINARY_RETRY_BASE_SECONDS=1.0
- UPLOAD_RATE_LIMIT_MAX_REQUESTS=10
- UPLOAD_RATE_LIMIT_WINDOW_SECONDS=60
- UPLOAD_QUEUE_RETRY_ATTEMPTS=8
- UPLOAD_QUEUE_RETRY_DELAY_SECONDS=10
- UPLOAD_QUEUE_RETRY_BACKOFF_MULTIPLIER=2.0
- UPLOAD_QUEUE_RETRY_MAX_DELAY_SECONDS=120
- UPLOAD_QUEUE_RETRY_JITTER_SECONDS=1.0

Quick notes:

1. Neon URL must start with postgresql+psycopg:// (not postgresql://).
2. If password has special chars, URL-encode it before saving.
3. Never paste old leaked secrets.
4. After updating env vars in Render, trigger a redeploy.

Post-deploy checks:

1. Open https://<your-render-domain>/health and expect {"status":"ok"}.
2. Call admin list endpoint with X-Admin-Api-Key and expect 200 OK.

Local preflight command (before pushing):

1. `./.venv/Scripts/python.exe scripts/check_env_ready.py`
2. Expect `ENV_CHECK=PASS`.
