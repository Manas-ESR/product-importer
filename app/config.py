import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# In deployment, override these with env vars
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://product_user:product_pass@localhost:5432/product_importer_db",
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
