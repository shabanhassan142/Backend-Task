from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import BookOut, BookListResponse
from app import crud

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=BookListResponse)
def list_books(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Case-insensitive category filter"),
    min_price: Optional[Decimal] = Query(default=None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(default=None, ge=0, description="Maximum price"),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=422,
            detail=f"min_price ({min_price}) must not be greater than max_price ({max_price}).",
        )

    total, items = crud.get_books(
        db,
        page=page,
        page_size=page_size,
        category=category,
        min_price=min_price,
        max_price=max_price,
    )
    return BookListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = crud.get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found.")
    return book
