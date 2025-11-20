import time
from typing import Any, Dict

from celery.utils.log import get_task_logger
import requests
from sqlalchemy import func

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Webhook

logger = get_task_logger(__name__)


@celery_app.task
def send_webhook_request(
    webhook_id: int, url: str, event_type: str, payload: Dict[str, Any]
):
    """
    Actually send the HTTP POST to the webhook URL and record status/latency.
    """
    start = time.time()
    status_code: int | None = None

    try:
        resp = requests.post(
            url,
            json={"event_type": event_type, "payload": payload},
            timeout=5,
        )
        status_code = resp.status_code
        logger.info("Webhook %s -> %s responded with %s", webhook_id, url, status_code)
    except Exception as exc:
        logger.warning("Webhook %s -> %s failed: %r", webhook_id, url, exc)

    duration_ms = int((time.time() - start) * 1000)

    # Save last_status_code and last_response_ms on the webhook row
    db = SessionLocal()
    try:
        hook = db.get(Webhook, webhook_id)
        if hook:
            hook.last_status_code = status_code
            hook.last_response_ms = duration_ms
            db.commit()
    finally:
        db.close()


@celery_app.task
def test_webhook_task(webhook_id: int):
    """
    Task used by the 'Test' button in the UI.
    Sends a simple test payload to the webhook URL.
    """
    db = SessionLocal()
    try:
        hook = db.get(Webhook, webhook_id)
        if not hook or not hook.enabled:
            return

        send_webhook_request.delay(
            hook.id,
            hook.url,
            "webhook.test",
            {"message": "test from product-importer"},
        )
    finally:
        db.close()


@celery_app.task
def trigger_webhooks_for_event(event_type: str, payload: Dict[str, Any]):
    """
    Trigger all enabled webhooks matching a given event_type.

    - event_type comparison is case-insensitive.
    - Each matching webhook gets its own send_webhook_request task.
    """
    db = SessionLocal()
    try:
        key = event_type.strip().lower()

        hooks = (
            db.query(Webhook)
            .filter(Webhook.enabled.is_(True))
            .filter(func.lower(Webhook.event_type) == key)
            .all()
        )

        logger.info("Triggering %d webhooks for event '%s'", len(hooks), key)

        for hook in hooks:
            send_webhook_request.delay(
                hook.id,
                hook.url,
                event_type,
                payload,
            )
    finally:
        db.close()
