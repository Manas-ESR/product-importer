from celery import Celery

from app.config import REDIS_URL

celery_app = Celery(
    "product_importer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

# Import tasks so Celery knows about them
from app.tasks import import_products, webhooks  # noqa: F401
