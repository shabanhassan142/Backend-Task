import logging
from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import books, scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Book Price Tracker API", version="1.0.0")


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")


app.include_router(books.router)
app.include_router(scrape.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
