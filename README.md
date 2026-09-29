# Book Price Tracker API

A FastAPI application that scrapes book data from [books.toscrape.com](https://books.toscrape.com),
stores it in PostgreSQL, and exposes a REST API to query and filter the results.

## Tech Stack

- Python 3.11 (Docker), 3.10+ for local runs
- FastAPI 0.141.1 + Uvicorn 0.54.0
- SQLAlchemy 2.1.1
- PostgreSQL 16 (Alpine)
- psycopg2-binary 2.9.13
- Pydantic 2.13.5 + pydantic-settings 2.15.0
- requests 2.34.2 + BeautifulSoup4 4.15.0 + lxml 6.1.3
- Docker & Docker Compose

---

## Quickstart (single command)

```bash
git clone https://github.com/shabanhassan142/Backend-Task.git
cd Backend-Task

# Optional: customise credentials or port
cp .env.example .env

docker-compose up --build
```

The API is live at **http://localhost:4000**
Interactive docs at **http://localhost:4000/docs**

No local Python, PostgreSQL, or any other dependency is required.
Everything runs inside Docker. The stack works with or without a `.env` file —
defaults are built into `docker-compose.yml`.

---

## Environment Variables

All variables have safe defaults. Override by creating a `.env` file from `.env.example`.

| Variable            | Default        | Description                        |
|---------------------|----------------|------------------------------------|
| `POSTGRES_USER`     | `postgres`     | PostgreSQL username                |
| `POSTGRES_PASSWORD` | `postgres`     | PostgreSQL password                |
| `POSTGRES_DB`       | `book_tracker` | PostgreSQL database name           |
| `POSTGRES_HOST`     | `db`           | Hostname (Docker service name)     |
| `POSTGRES_PORT`     | `5432`         | PostgreSQL port (internal)         |
| `APP_PORT`          | `4000`         | Host port mapped to the app (8000) |

`.env` is git-ignored and never committed. `.env.example` is committed as a reference.

---

## Running the Scraper

The scraper targets all 50 categories on books.toscrape.com and collects
1000 books with title, price, rating, availability, category, UPC, and stock quantity.
Re-running upserts existing rows — no duplicates are ever created.

### Via the API (recommended)

```bash
# Trigger scrape in the background — returns 202 immediately
curl -X POST http://localhost:4000/scrape

# Poll status until running is false
curl http://localhost:4000/scrape/status
```

The `POST /scrape` response always shows zero stats — that is by design.
The real numbers (scraped, inserted, updated, failed) appear in `GET /scrape/status`
once the background task completes.

### Inside the running container

```bash
docker-compose exec app python -m app.scraper.run
```

### Locally (requires Python 3.10+ and a reachable Postgres)

All five `POSTGRES_*` variables must be set. Copy `.env.example` to `.env` and update
`POSTGRES_HOST` to `localhost` and `POSTGRES_PORT` to the port your local Postgres
is listening on, then run:

```bash
cp .env.example .env
# edit .env: set POSTGRES_HOST=localhost and POSTGRES_PORT=<your port>
pip install -r requirements.txt
python -m app.scraper.run
```

---

## API Endpoints

### GET /health

```bash
curl http://localhost:4000/health
```

```json
{"status": "ok"}
```

---

### GET /books

Paginated list with optional filters. All parameters are combinable.

| Parameter   | Type    | Default | Constraints        | Description                        |
|-------------|---------|---------|--------------------|------------------------------------|
| `page`      | integer | 1       | ≥ 1                | Page number                        |
| `page_size` | integer | 20      | 1 – 100            | Items per page                     |
| `category`  | string  | —       | case-insensitive   | Exact category match               |
| `min_price` | decimal | —       | ≥ 0                | Minimum price (inclusive)          |
| `max_price` | decimal | —       | ≥ 0                | Maximum price (inclusive)          |

If `min_price > max_price` the API returns **422** with a clear message.

#### Pagination

```bash
curl "http://localhost:4000/books?page=1&page_size=3"
```

```json
{
  "total": 1000,
  "page": 1,
  "page_size": 3,
  "items": [
    {
      "id": 1,
      "title": "It's Only the Himalayas",
      "price": 45.17,
      "rating": 2,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 19,
      "product_url": "https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html",
      "upc": "a22124811bfa8350",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 2,
      "title": "A Summer In Europe",
      "price": 44.34,
      "rating": 2,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 7,
      "product_url": "https://books.toscrape.com/catalogue/a-summer-in-europe_458/index.html",
      "upc": "cc1936a9f4e93477",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 3,
      "title": "The Great Railway Bazaar",
      "price": 30.54,
      "rating": 1,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 6,
      "product_url": "https://books.toscrape.com/catalogue/the-great-railway-bazaar_446/index.html",
      "upc": "48736df57e7bec9f",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    }
  ]
}
```

#### Category filter (case-insensitive)

```bash
curl "http://localhost:4000/books?category=Mystery&page_size=3"
```

```json
{
  "total": 32,
  "page": 1,
  "page_size": 3,
  "items": [
    {
      "id": 10,
      "title": "Sharp Objects",
      "price": 47.82,
      "rating": 4,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 20,
      "product_url": "https://books.toscrape.com/catalogue/sharp-objects_997/index.html",
      "upc": "e00eb4fd7b871a48",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 12,
      "title": "In a Dark, Dark Wood",
      "price": 19.63,
      "rating": 1,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 18,
      "product_url": "https://books.toscrape.com/catalogue/in-a-dark-dark-wood_963/index.html",
      "upc": "19ed25f4641d5efd",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 14,
      "title": "The Past Never Ends",
      "price": 56.5,
      "rating": 4,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 16,
      "product_url": "https://books.toscrape.com/catalogue/the-past-never-ends_942/index.html",
      "upc": "5ee94540d0749ea0",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    }
  ]
}
```

#### Price range filter

```bash
curl "http://localhost:4000/books?min_price=10&max_price=15&page_size=3"
```

```json
{
  "total": 106,
  "page": 1,
  "page_size": 3,
  "items": [
    {
      "id": 17,
      "title": "That Darkness (Gardiner and Renner #1)",
      "price": 13.92,
      "rating": 1,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 14,
      "product_url": "https://books.toscrape.com/catalogue/that-darkness-gardiner-and-renner-1_743/index.html",
      "upc": "0c7b9cf2b7662b65",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 19,
      "title": "Tastes Like Fear (DI Marnie Rome #3)",
      "price": 10.69,
      "rating": 1,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 14,
      "product_url": "https://books.toscrape.com/catalogue/tastes-like-fear-di-marnie-rome-3_742/index.html",
      "upc": "2d1e337aaf341858",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 25,
      "title": "Hide Away (Eve Duncan #20)",
      "price": 11.84,
      "rating": 1,
      "category": "Mystery",
      "availability": "In stock",
      "stock_quantity": 12,
      "product_url": "https://books.toscrape.com/catalogue/hide-away-eve-duncan-20_620/index.html",
      "upc": "bddc6fd036eb6279",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    }
  ]
}
```

#### Combined filters

```bash
curl "http://localhost:4000/books?category=Travel&min_price=30&page_size=3"
```

```json
{
  "total": 9,
  "page": 1,
  "page_size": 3,
  "items": [
    {
      "id": 1,
      "title": "It's Only the Himalayas",
      "price": 45.17,
      "rating": 2,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 19,
      "product_url": "https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html",
      "upc": "a22124811bfa8350",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 2,
      "title": "A Summer In Europe",
      "price": 44.34,
      "rating": 2,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 7,
      "product_url": "https://books.toscrape.com/catalogue/a-summer-in-europe_458/index.html",
      "upc": "cc1936a9f4e93477",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    },
    {
      "id": 3,
      "title": "The Great Railway Bazaar",
      "price": 30.54,
      "rating": 1,
      "category": "Travel",
      "availability": "In stock",
      "stock_quantity": 6,
      "product_url": "https://books.toscrape.com/catalogue/the-great-railway-bazaar_446/index.html",
      "upc": "48736df57e7bec9f",
      "scraped_at": "2026-09-29T21:16:44.471988Z"
    }
  ]
}
```

---

### GET /books/{id}

```bash
curl http://localhost:4000/books/1
```

```json
{
  "id": 1,
  "title": "It's Only the Himalayas",
  "price": 45.17,
  "rating": 2,
  "category": "Travel",
  "availability": "In stock",
  "stock_quantity": 19,
  "product_url": "https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html",
  "upc": "a22124811bfa8350",
  "scraped_at": "2026-09-29T21:16:44.471988Z"
}
```

Not found:

```bash
curl http://localhost:4000/books/999999
```

```json
{"detail": "Book with id 999999 not found."}
```

---

### POST /scrape

Triggers a full scrape in the background. Returns **202** immediately.
A second request while a scrape is already running returns **409**.

```bash
curl -X POST http://localhost:4000/scrape
```

```json
{
  "message": "Scrape started in background.",
  "stats": {
    "scraped": 0,
    "inserted": 0,
    "updated": 0,
    "failed": 0
  }
}
```

The `stats` block in this response is always zero — it reflects the state at the moment
of the 202 response, before the background task has run. See `GET /scrape/status` for the
real numbers.

---

### GET /scrape/status

```bash
curl http://localhost:4000/scrape/status
```

```json
{
  "running": false,
  "started_at": "2026-09-29T21:14:30.852003+00:00",
  "finished_at": "2026-09-29T21:16:47.485974+00:00",
  "last_stats": {
    "scraped": 1000,
    "inserted": 1000,
    "updated": 0,
    "failed": 0
  },
  "last_error": null
}
```

On a re-run after data already exists, `inserted` will be 0 and `updated` will be 1000.

---

## Project Structure

```
book-price-tracker/
├── app/
│   ├── main.py            # FastAPI app, startup event, router registration
│   ├── config.py          # Pydantic Settings — reads env vars, builds DB URL
│   ├── database.py        # SQLAlchemy engine (with retry), SessionLocal, get_db
│   ├── models.py          # Book ORM model
│   ├── schemas.py         # Pydantic v2 request/response models
│   ├── crud.py            # DB query functions (filter, paginate, get by id)
│   ├── routers/
│   │   ├── books.py       # GET /books, GET /books/{id}
│   │   └── scrape.py      # POST /scrape, GET /scrape/status
│   └── scraper/
│       ├── scraper.py     # Scraping logic, upsert, run_scraper()
│       └── run.py         # CLI entry: python -m app.scraper.run
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Database Schema

Table: `books`

| Column           | Type                       | Constraints              |
|------------------|----------------------------|--------------------------|
| `id`             | integer                    | PK, autoincrement        |
| `title`          | varchar                    | NOT NULL                 |
| `price`          | numeric(10,2)              | NOT NULL                 |
| `rating`         | integer                    | nullable (1–5)           |
| `category`       | varchar                    | nullable, indexed        |
| `availability`   | varchar                    | nullable                 |
| `stock_quantity` | integer                    | nullable                 |
| `product_url`    | varchar                    | NOT NULL, UNIQUE         |
| `upc`            | varchar                    | nullable                 |
| `scraped_at`     | timestamp with time zone   | NOT NULL                 |

---

## Design Notes

**No duplicates.** The scraper uses `INSERT ... ON CONFLICT (product_url) DO UPDATE`.
Each book's detail page URL is unique on the site, so re-running the scraper
updates existing rows rather than inserting duplicates.

**COALESCE on upsert.** When a detail page fails to load, `upc` and `stock_quantity`
come back as `NULL`. The upsert uses `COALESCE(excluded.upc, books.upc)` so a failed
detail fetch never overwrites a previously stored real value.

**Decimal prices.** Prices are stored as `numeric(10,2)` in Postgres and serialized
as JSON numbers (e.g. `45.17`) via a `@field_serializer` on the Pydantic model.
The `£` sign and encoding artefacts (`Â£`) are stripped before parsing.

**Retries and error handling.** Every HTTP request uses a 15-second timeout and
3 retries with exponential backoff. A bad page or missing field is logged and skipped.
One failed book never stops the rest of the run.

**Scrape lock.** `POST /scrape` uses a `threading.Lock` to ensure only one scrape
runs at a time. A second `POST` while a scrape is active returns **409 Conflict**.
The flag is always reset in a `finally` block even if the scraper crashes.

**Category names.** The scraper reads category names directly from the sidebar links
on books.toscrape.com. Two categories have unusual names that are not typos:
`Default` (152 books) and `Add a comment` (67 books). These are real category names
on the target site.

**Port layout.**

| Service    | Inside container | Host port       |
|------------|-----------------|-----------------|
| FastAPI    | 8000            | 4000            |
| PostgreSQL | 5432            | not exposed     |

FastAPI and Postgres communicate over Docker's internal network (`db:5432`).
Postgres is never reachable from the host, which prevents conflicts with any
existing local Postgres instances.

**Python version.** Docker uses Python 3.11. For local runs, Python 3.10 or newer is recommended.
