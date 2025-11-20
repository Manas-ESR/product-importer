from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductOut, ProductList
from app.tasks.webhooks import trigger_webhooks_for_event

# NOTE: no prefix here; main.py adds prefix="/api"
router = APIRouter(tags=["products"])


def _product_payload(product: Product) -> dict:
    """Serialize Product to JSON-safe dict for Celery/webhooks."""
    price = product.price
    price_value = float(price) if price is not None else None
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": price_value,
        "active": product.active,
    }


@router.get("/products", response_model=ProductList)
def list_products(
    sku: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if sku:
        # SKUs stored uppercased; filter case-insensitively
        query = query.filter(func.upper(Product.sku).like(f"%{sku.upper()}%"))
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))
    if description:
        query = query.filter(Product.description.ilike(f"%{description}%"))
    if active is not None:
        query = query.filter(Product.active == active)

    total = query.count()
    items = (
        query.order_by(Product.id).offset((page - 1) * page_size).limit(page_size).all()
    )

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    sku_normalized = payload.sku.strip().upper()
    existing = db.query(Product).filter(Product.sku == sku_normalized).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Product with this SKU already exists"
        )

    product = Product(
        sku=sku_normalized,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        active=payload.active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Fire webhook asynchronously, but never break the request if Celery/json fails
    try:
        trigger_webhooks_for_event.delay(
            "product.created",
            _product_payload(product),
        )
    except Exception:
        pass

    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.name is not None:
        product.name = payload.name
    if payload.description is not None:
        product.description = payload.description
    if payload.price is not None:
        product.price = payload.price
    if payload.active is not None:
        product.active = payload.active

    db.commit()
    db.refresh(product)

    try:
        trigger_webhooks_for_event.delay(
            "product.updated",
            _product_payload(product),
        )
    except Exception:
        pass

    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sku_value = product.sku
    db.delete(product)
    db.commit()

    try:
        trigger_webhooks_for_event.delay(
            "product.deleted",
            {"id": product_id, "sku": sku_value},
        )
    except Exception:
        pass

    return


@router.delete("/products")
def delete_all_products(db: Session = Depends(get_db)):
    deleted = db.query(Product).delete()
    db.commit()

    try:
        trigger_webhooks_for_event.delay(
            "product.bulk_deleted",
            {"deleted": deleted},
        )
    except Exception:
        pass

    return {"deleted": deleted}
