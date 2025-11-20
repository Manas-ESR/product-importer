from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ----- Product -----


class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ProductList(BaseModel):
    items: list[ProductOut]
    page: int
    page_size: int
    total: int


# ----- Upload job -----


class UploadJobOut(BaseModel):
    id: int
    filename: str
    status: str
    total_rows: Optional[int] = None
    processed_rows: int
    percentage: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True


# ----- Webhook -----


class WebhookBase(BaseModel):
    url: str
    event_type: str
    enabled: bool = True


class WebhookCreate(WebhookBase):
    pass


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    event_type: Optional[str] = None
    enabled: Optional[bool] = None


class WebhookOut(WebhookBase):
    id: int
    last_test_status_code: Optional[int] = None
    last_test_response_time_ms: Optional[int] = None
    last_test_error: Optional[str] = None

    class Config:
        orm_mode = True
