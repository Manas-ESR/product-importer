from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import get_db
from app.models import UploadJob
from app.schemas import UploadJobOut
from app.tasks.import_products import import_products_task

router = APIRouter(tags=["uploads"])


@router.post("/uploads")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    tmp_name = f"{uuid4()}.csv"
    tmp_path = UPLOAD_DIR / tmp_name

    contents = await file.read()
    tmp_path.write_bytes(contents)

    job = UploadJob(
        filename=file.filename,
        status="pending",
        total_rows=None,
        processed_rows=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    import_products_task.delay(job.id, str(tmp_path))

    return {"job_id": job.id, "status": job.status}


@router.get("/uploads/{job_id}", response_model=UploadJobOut)
def get_upload_status(job_id: int, db: Session = Depends(get_db)):
    job = db.get(UploadJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")

    percentage = None
    if job.total_rows and job.total_rows > 0:
        percentage = round(job.processed_rows * 100.0 / job.total_rows, 2)

    return UploadJobOut(
        id=job.id,
        filename=job.filename,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        percentage=percentage,
        error_message=job.error_message,
    )
