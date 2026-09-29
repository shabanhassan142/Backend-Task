"""
CLI entry point: python -m app.scraper.run
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

from app.database import SessionLocal
from app.scraper.scraper import run_scraper


def main():
    db = SessionLocal()
    try:
        stats = run_scraper(db)
        print("\n=== Scraper Results ===")
        print(f"  Scraped  : {stats['scraped']}")
        print(f"  Inserted : {stats['inserted']}")
        print(f"  Updated  : {stats['updated']}")
        print(f"  Failed   : {stats['failed']}")
        # Exit 1 if nothing was scraped or upsert failed (inserted+updated == 0 but scraped > 0)
        if stats["scraped"] == 0 or (stats["inserted"] + stats["updated"] == 0 and stats["scraped"] > 0):
            sys.exit(1)
        sys.exit(0)
    finally:
        db.close()


if __name__ == "__main__":
    main()
