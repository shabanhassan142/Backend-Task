import threading
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.schemas import ScrapeResponse, ScrapeStats
from app.database import SessionLocal
from app.scraper.scraper import run_scraper

router = APIRouter(prefix="/scrape", tags=["scrape"])

# --- scrape state (module-level, single process) ---
_lock = threading.Lock()
_running = False
_started_at: Optional[datetime] = None
_finished_at: Optional[datetime] = None
_last_stats: Optional[dict] = None
_last_error: Optional[str] = None


def _run_scraper_task():
    global _running, _started_at, _finished_at, _last_stats, _last_error
    db = SessionLocal()
    try:
        _last_stats = None
        _last_error = None
        stats = run_scraper(db)
        _last_stats = stats
    except Exception as e:
        _last_error = str(e)
    finally:
        db.close()
        _finished_at = datetime.now(timezone.utc)
        with _lock:
            _running = False


@router.post("", status_code=202, response_model=ScrapeResponse)
def trigger_scrape(background_tasks: BackgroundTasks):
    global _running, _started_at, _finished_at

    with _lock:
        if _running:
            raise HTTPException(status_code=409, detail="A scrape is already running.")
        _running = True
        _started_at = datetime.now(timezone.utc)
        _finished_at = None

    background_tasks.add_task(_run_scraper_task)

    return ScrapeResponse(
        message="Scrape started in background.",
        stats=ScrapeStats(scraped=0, inserted=0, updated=0, failed=0),
    )


@router.get("/status")
def scrape_status():
    return {
        "running": _running,
        "started_at": _started_at.isoformat() if _started_at else None,
        "finished_at": _finished_at.isoformat() if _finished_at else None,
        "last_stats": _last_stats,
        "last_error": _last_error,
    }
