from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_serializer
from pydantic import ConfigDict


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: Decimal
    rating: Optional[int]
    category: Optional[str]
    availability: Optional[str]
    stock_quantity: Optional[int]
    product_url: str
    upc: Optional[str]
    scraped_at: datetime

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> float:
        return float(value)


class BookListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[BookOut]


class ScrapeStats(BaseModel):
    scraped: int
    inserted: int
    updated: int
    failed: int


class ScrapeResponse(BaseModel):
    message: str
    stats: ScrapeStats
