import csv
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Product, UploadJob
from app.tasks.webhooks import trigger_webhooks_for_event


@celery_app.task
def import_products_task(job_id: int, file_path: str):
    db = SessionLocal()
    job = db.get(UploadJob, job_id)
    if not job:
        db.close()
        return

    job.status = "parsing"
    job.started_at = datetime.utcnow()
    db.commit()

    path = Path(file_path)
    if not path.exists():
        job.status = "failed"
        job.error_message = "Uploaded file not found on server"
        job.finished_at = datetime.utcnow()
        db.commit()
        db.close()
        return

    # Count total rows for progress (minus header)
    with path.open("r", newline="") as f:
        total = sum(1 for _ in f) - 1
    if total < 0:
        total = 0

    job.total_rows = total
    job.status = "importing"
    db.commit()

    processed = 0
    batch_size = 2000

    try:
        with path.open("r", newline="") as f:
            reader = csv.DictReader(f)
            batch: list[dict] = []

            for row in reader:
                batch.append(row)
                if len(batch) >= batch_size:
                    _upsert_batch(db, batch)
                    processed += len(batch)  # count CSV rows, even if deduped
                    job.processed_rows = processed
                    db.commit()
                    batch.clear()

            if batch:
                _upsert_batch(db, batch)
                processed += len(batch)
                job.processed_rows = processed
                db.commit()

        job.status = "completed"
        job.finished_at = datetime.utcnow()
        db.commit()

        trigger_webhooks_for_event.delay(
            "product.import.completed",
            {"job_id": job_id, "processed": processed},
        )

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()


def _upsert_batch(db, rows: list[dict]):
    """
    Upsert a batch of CSV rows into the products table.

    - Normalize SKU to upper-case for case-insensitive uniqueness.
    - Deduplicate within the batch by SKU so ON CONFLICT doesn't hit the same
      row twice in a single INSERT.
    - Last occurrence of a SKU inside the batch wins.
    """
    items_by_sku: dict[str, dict] = {}

    for r in rows:
        # Try different capitalizations for CSV headers
        sku = (r.get("sku") or r.get("SKU") or "").strip()
        name = (r.get("name") or r.get("Name") or "").strip()
        description = (r.get("description") or r.get("Description") or "").strip()
        price_raw = r.get("price") or r.get("Price") or None

        if not sku or not name:
            # Skip rows without essential fields
            continue

        sku_upper = sku.upper()

        price = None
        if price_raw:
            try:
                price = Decimal(price_raw)
            except Exception:
                price = None

        # Last row for a given SKU within this batch wins
        items_by_sku[sku_upper] = {
            "sku": sku_upper,
            "name": name,
            "description": description,
            "price": price,
        }

    values = list(items_by_sku.values())
    if not values:
        return

    stmt = insert(Product).values(values)
    # Conflict on SKU (case-insensitive handled by normalizing to upper-case before insert)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Product.sku],
        set_={
            "name": stmt.excluded.name,
            "description": stmt.excluded.description,
            "price": stmt.excluded.price,
            "updated_at": datetime.utcnow(),
        },
    )
    db.execute(stmt)
    db.commit()
