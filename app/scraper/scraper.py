import logging
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Book

logger = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com"
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
MAX_WORKERS = 5
TIMEOUT = 15
MAX_RETRIES = 3


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "BookPriceTracker/1.0"})
    return s


def fetch(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL with retries and backoff. Returns BeautifulSoup or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.encoding = "utf-8"
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.warning(f"Fetch attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    logger.error(f"All retries exhausted for {url}")
    return None


def get_categories(session: requests.Session) -> list[tuple[str, str]]:
    """Return list of (category_name, category_url) from the sidebar, skipping root 'Books'."""
    soup = fetch(session, BASE_URL)
    if not soup:
        return []
    nav = soup.select("ul.nav-list > li > ul > li > a")
    categories = []
    for a in nav:
        name = a.get_text(strip=True)
        url = BASE_URL + "/" + a["href"].strip()
        categories.append((name, url))
    return categories


def parse_price(text: str) -> Optional[Decimal]:
    try:
        cleaned = text.replace("\u00a3", "").replace("\u00c2\u00a3", "").replace("Â£", "").strip()
        return Decimal(cleaned)
    except (InvalidOperation, AttributeError):
        return None


def parse_rating(tag) -> Optional[int]:
    try:
        classes = tag.get("class", [])
        for cls in classes:
            if cls in RATING_MAP:
                return RATING_MAP[cls]
    except Exception:
        pass
    return None


def parse_availability(text: str) -> str:
    return " ".join(text.split())


def scrape_detail(session: requests.Session, url: str) -> dict:
    """Scrape UPC and exact stock quantity from detail page."""
    result = {"upc": None, "stock_quantity": None}
    soup = fetch(session, url)
    if not soup:
        return result
    try:
        table = soup.find("table", class_="table-striped")
        if table:
            rows = {
                tr.find("th").get_text(strip=True): tr.find("td").get_text(strip=True)
                for tr in table.find_all("tr")
            }
            result["upc"] = rows.get("UPC")
            avail_text = rows.get("Availability", "")
            match = re.search(r"\d+", avail_text)
            if match:
                result["stock_quantity"] = int(match.group())
    except Exception as e:
        logger.warning(f"Detail parse error for {url}: {e}")
    return result


def scrape_category(
    session: requests.Session, category_name: str, category_url: str, stats: dict
) -> list[dict]:
    """Scrape all pages in a category and return list of book dicts."""
    books = []
    page_url = category_url

    while page_url:
        soup = fetch(session, page_url)
        if not soup:
            logger.error(f"Failed to load category page: {page_url}")
            stats["failed"] += 1
            break

        articles = soup.select("article.product_pod")
        for article in articles:
            try:
                # Title
                title_tag = article.select_one("h3 > a")
                if not title_tag:
                    logger.warning(f"Missing title tag in {page_url}, skipping book.")
                    stats["failed"] += 1
                    continue
                title = title_tag.get("title", title_tag.get_text(strip=True))

                # Product URL
                relative = (
                    title_tag["href"]
                    .replace("../../../", "catalogue/")
                    .replace("../../", "catalogue/")
                    .replace("../", "catalogue/")
                )
                if not relative.startswith("catalogue/"):
                    relative = "catalogue/" + relative
                product_url = BASE_URL + "/" + relative

                # Price
                price_tag = article.select_one("p.price_color")
                price = parse_price(price_tag.get_text()) if price_tag else None
                if price is None:
                    logger.warning(f"Missing/bad price for '{title}', skipping book.")
                    stats["failed"] += 1
                    continue

                # Rating
                rating_tag = article.select_one("p.star-rating")
                rating = parse_rating(rating_tag) if rating_tag else None

                # Availability
                avail_tag = article.select_one("p.availability")
                availability = parse_availability(avail_tag.get_text()) if avail_tag else None

                books.append({
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "category": category_name,
                    "availability": availability,
                    "product_url": product_url,
                    "upc": None,
                    "stock_quantity": None,
                })
            except Exception as e:
                logger.warning(f"Error parsing article in {page_url}: {e}")
                stats["failed"] += 1
                continue

        # Pagination
        next_btn = soup.select_one("li.next > a")
        if next_btn:
            base = page_url.rsplit("/", 1)[0]
            page_url = base + "/" + next_btn["href"]
        else:
            page_url = None

    return books


def enrich_with_details(
    session: requests.Session, books: list[dict], stats: dict
) -> list[dict]:
    """Use thread pool to fetch detail pages for UPC and stock_quantity."""

    def fetch_detail(book: dict) -> dict:
        detail = scrape_detail(session, book["product_url"])
        book.update(detail)
        return book

    enriched = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_detail, book): book for book in books}
        for future in as_completed(futures):
            try:
                enriched.append(future.result())
            except Exception as e:
                logger.warning(f"Detail fetch failed: {e}")
                stats["failed"] += 1
                enriched.append(futures[future])
    return enriched


def upsert_books(db: Session, books: list[dict]) -> tuple[int, int]:
    """Upsert books into DB. Returns (inserted, updated).
    - Uses COALESCE so a NULL upc/stock_quantity from a failed detail page
      never overwrites an existing real value.
    - Pre-checks existing URLs to accurately count inserted vs updated.
    """
    if not books:
        return 0, 0

    now = datetime.now(timezone.utc)

    urls = [b["product_url"] for b in books]
    existing = {
        row[0] for row in db.execute(select(Book.product_url).where(Book.product_url.in_(urls)))
    }

    inserted = 0
    updated = 0

    for book in books:
        stmt = insert(Book).values(
            title=book["title"],
            price=book["price"],
            rating=book["rating"],
            category=book["category"],
            availability=book["availability"],
            stock_quantity=book["stock_quantity"],
            product_url=book["product_url"],
            upc=book["upc"],
            scraped_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["product_url"],
            set_={
                "title": stmt.excluded.title,
                "price": stmt.excluded.price,
                "rating": stmt.excluded.rating,
                "category": stmt.excluded.category,
                "availability": stmt.excluded.availability,
                # Never overwrite with NULL — keep existing value if new value is NULL
                "stock_quantity": func.coalesce(stmt.excluded.stock_quantity, Book.stock_quantity),
                "upc": func.coalesce(stmt.excluded.upc, Book.upc),
                "scraped_at": now,
            },
        )
        db.execute(stmt)
        if book["product_url"] in existing:
            updated += 1
        else:
            inserted += 1

    db.commit()
    return inserted, updated


def run_scraper(db: Session) -> dict:
    """Main entry point. Returns stats dict."""
    session = make_session()
    stats = {"scraped": 0, "inserted": 0, "updated": 0, "failed": 0}

    logger.info("Fetching categories...")
    categories = get_categories(session)
    if not categories:
        logger.error("No categories found.")
        return stats

    logger.info(f"Found {len(categories)} categories.")

    all_books = []
    for cat_name, cat_url in categories:
        logger.info(f"Scraping category: {cat_name}")
        try:
            books = scrape_category(session, cat_name, cat_url, stats)
            logger.info(f"  {cat_name}: {len(books)} books collected")
            all_books.extend(books)
        except Exception as e:
            logger.error(f"Category '{cat_name}' failed entirely: {e}")
            stats["failed"] += 1

    stats["scraped"] = len(all_books)
    logger.info(f"Total scraped: {len(all_books)} books. Fetching detail pages...")

    all_books = enrich_with_details(session, all_books, stats)

    logger.info("Upserting to database...")
    try:
        inserted, updated = upsert_books(db, all_books)
        stats["inserted"] = inserted
        stats["updated"] = updated
    except Exception as e:
        logger.error(f"DB upsert failed: {e}")
        db.rollback()
        stats["failed"] += len(all_books)

    logger.info(f"Done. Stats: {stats}")
    return stats
