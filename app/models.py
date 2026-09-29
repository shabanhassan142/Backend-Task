from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    availability: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    product_url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    upc: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
