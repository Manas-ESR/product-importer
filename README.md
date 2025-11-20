# Product Importer

A small but production-style web application that:

- Uploads a large CSV file of products (up to ~500,000 records)
- Streams it to PostgreSQL via a background Celery worker
- Provides a product management UI (CRUD + filtering + pagination)
- Supports bulk delete from the UI
- Lets you configure webhooks and trigger them on product events (e.g. `product.created`)

Tech stack:

- **Backend:** FastAPI
- **Async workers:** Celery
- **Broker / Result backend:** Redis
- **Database:** PostgreSQL (SQLAlchemy + Alembic)
- **Templates:** Jinja2 + simple HTML/JS

---

## Architecture Overview

### High-level components

- **FastAPI app (`app.main`)**
  - Serves HTML pages: `/upload`, `/products`, `/webhooks`
  - Exposes JSON APIs under `/api/...` (uploads, products, webhooks)
  - Uses `Jinja2Templates` for rendering templates from `templates/`

- **Database layer**
  - SQLAlchemy ORM models in `app.models`
  - Session handling in `app.database` (`SessionLocal`, `get_db`)
  - Alembic migrations under `alembic/`
  - Main tables:
    - `products`: SKU, name, description, price, active, created/updated timestamps
    - `upload_jobs`: tracks CSV upload status + progress
    - `webhooks`: stores webhook URL, event type, enabled flag and last test status

- **Celery worker (`app.celery_app`)**
  - Uses Redis as broker + result backend
  - Key tasks:
    - `import_products_task`: parses CSV rows in batches and upserts into `products`
    - `trigger_webhooks_for_event`: finds matching `webhooks` and schedules HTTP calls
    - `send_webhook_request`: performs the actual POST with JSON payload
    - `test_webhook_task`: test-fire one webhook and record the status code + response time

- **Upload flow (long-running)**
  1. User uploads a CSV via the `/upload` page.
  2. FastAPI saves the file to disk and creates an `upload_jobs` row with status `pending`.
  3. FastAPI enqueues `import_products_task(upload_job_id, file_path)` via Celery.
  4. Celery worker:
     - Opens the CSV, streams it row-by-row (no loading whole file into memory).
     - Parses in batches (e.g., 1,000 rows at a time).
     - Uses PostgreSQL `INSERT ... ON CONFLICT (sku) DO UPDATE` so SKU is unique
       and duplicates overwrite by SKU (case-insensitive).
     - Periodically updates `upload_jobs.progress` and `status`.
  5. The frontend polls `/api/uploads/{id}` or uses a similar mechanism to show:
     - “Parsing CSV…”, “Validating…”, percent progress, and final status.

This design avoids blocking HTTP requests and works even for very large CSVs or platforms with a 30-second request timeout (e.g. Heroku, Render).
