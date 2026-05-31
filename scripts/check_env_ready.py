from __future__ import annotations

from pathlib import Path

REQUIRED_KEYS = [
    "DATABASE_URL",
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
    "ADMIN_API_KEY",
    "ALLOW_INSECURE_ADMIN",
]

PLACEHOLDER_TOKENS = (
    "ROTATE_NEON_PASSWORD_NOW",
    "<your_",
    "replace_with_",
    "<neon_",
)


def load_dotenv(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value

    return values


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    env_values = load_dotenv(project_root / ".env")

    errors: list[str] = []

    for key in REQUIRED_KEYS:
        if not env_values.get(key):
            errors.append(f"Missing required key: {key}")

    db_url = env_values.get("DATABASE_URL", "")
    if db_url and not db_url.startswith("postgresql+psycopg://"):
        errors.append("DATABASE_URL must start with postgresql+psycopg://")

    lower_blob = "\n".join(f"{k}={v}" for k, v in env_values.items()).lower()
    for token in PLACEHOLDER_TOKENS:
        if token.lower() in lower_blob:
            errors.append(f"Placeholder token found: {token}")

    insecure_admin = env_values.get("ALLOW_INSECURE_ADMIN", "").strip().lower()
    if insecure_admin and insecure_admin != "false":
        errors.append("ALLOW_INSECURE_ADMIN must be false for production")

    admin_key = env_values.get("ADMIN_API_KEY", "")
    if admin_key and len(admin_key) < 32:
        errors.append("ADMIN_API_KEY should be at least 32 characters")

    if errors:
        print("ENV_CHECK=FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("ENV_CHECK=PASS")
    print("All required production keys are present and look valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
