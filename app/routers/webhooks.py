from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Webhook
from app.tasks.webhooks import test_webhook_task

router = APIRouter(tags=["webhooks"])  # main.py adds prefix="/api"


class WebhookIn(BaseModel):
    url: str
    event_type: str
    enabled: bool = True


def _serialize_webhook(h: Webhook) -> dict:
    return {
        "id": h.id,
        "url": h.url,
        "event_type": h.event_type,
        "enabled": h.enabled,
        "last_status_code": h.last_status_code,
        "last_response_ms": h.last_response_ms,
    }


@router.get("/webhooks")
def list_webhooks(db: Session = Depends(get_db)) -> List[dict]:
    hooks = db.query(Webhook).order_by(Webhook.id).all()
    return [_serialize_webhook(h) for h in hooks]


@router.post("/webhooks")
def create_webhook(payload: WebhookIn, db: Session = Depends(get_db)) -> dict:
    url = payload.url.strip()
    event_type = payload.event_type.strip()
    if not url or not event_type:
        raise HTTPException(status_code=400, detail="url and event_type are required")

    hook = Webhook(
        url=url,
        event_type=event_type,
        enabled=payload.enabled,
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return _serialize_webhook(hook)


@router.put("/webhooks/{webhook_id}")
def update_webhook(
    webhook_id: int,
    payload: WebhookIn,
    db: Session = Depends(get_db),
) -> dict:
    hook = db.get(Webhook, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    hook.url = payload.url.strip()
    hook.event_type = payload.event_type.strip()
    hook.enabled = payload.enabled

    db.commit()
    db.refresh(hook)
    return _serialize_webhook(hook)


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)) -> dict:
    hook = db.get(Webhook, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    db.delete(hook)
    db.commit()
    return {"ok": True}


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: int, db: Session = Depends(get_db)) -> dict:
    hook = db.get(Webhook, webhook_id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_webhook_task.delay(webhook_id)
    return {"ok": True}
