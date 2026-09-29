from decimal import Decimal
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Book


def get_books(
    db: Session,
    page: int,
    page_size: int,
    category: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
) -> tuple[int, list[Book]]:
    q = select(Book)

    if category is not None:
        q = q.where(func.lower(Book.category) == category.lower())
    if min_price is not None:
        q = q.where(Book.price >= min_price)
    if max_price is not None:
        q = q.where(Book.price <= max_price)

    count_q = select(func.count()).select_from(q.subquery())
    total = db.execute(count_q).scalar_one()

    q = q.order_by(Book.id).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(q).scalars().all())

    return total, items


def get_book_by_id(db: Session, book_id: int) -> Optional[Book]:
    return db.get(Book, book_id)
