# Neon Free Database Setup

## 1. Tao database free tren Neon

1. Vao https://neon.tech
2. Dang ky / dang nhap tai khoan.
3. Tao mot project moi.
4. Dat ten database, user, password theo y ban.
5. Neon se cap cho ban mot `DATABASE_URL` san.

## 2. Chuoi ket noi dung cho project nay

Project nay dung SQLAlchemy + Alembic, nen `DATABASE_URL` can theo format:

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require
```

Vi du voi Neon:

```env
DATABASE_URL=postgresql+psycopg://neondb_owner:YOUR_PASSWORD@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/python_backend?sslmode=require
```

Neu Neon cung cap connection string dang `postgresql://...`, ban chi can doi `postgresql://` thanh `postgresql+psycopg://`.

Luu y endpoint:

- URL co `-pooler` trong host: nen dung cho runtime app.
- URL khong co `-pooler` (direct): uu tien dung cho Alembic migration.

## 3. Doi file `.env`

Mo file `.env` trong `Python Backend/` va cap nhat:

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require
```

Giu nguyen cac bien khac:

```env
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
ADMIN_API_KEY=...
ALLOW_INSECURE_ADMIN=false
```

## 4. Chay Alembic migration len Neon

Chay tu thu muc `Python Backend/`:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Neu ban muon chay migration bang direct URL tam thoi (khong doi file `.env`), dung:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
$env:DATABASE_URL="postgresql+psycopg://neondb_owner:<NEON_PASSWORD>@<direct-host>/neondb?sslmode=require"
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:DATABASE_URL
```

Neu muon kiem tra Alembic dang nhin dung URL:

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
.\.venv\Scripts\python.exe -c "from app.core.config import settings; print(settings.database_url)"
```

## 5. Chay app

```powershell
Set-Location "c:/Users/ADMIN/OneDrive/Desktop/Thư mục mới (2)/Python Backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## 6. Luu y quan trong

- Neu ban thu tren Neon, hay dam bao URL co `sslmode=require`.
- Khong de `DATABASE_URL=sqlite:///./app.db` neu muon chay production / cloud.
- Neu migration bao loi connection, kiem tra lai:
  - host
  - port
  - database name
  - user
  - password
  - SSL

## 7. Sau khi migration

Khi `alembic upgrade head` chay xong, backend se dung PostgreSQL Neon thay vi SQLite.
