# Saral Data Engineering Pipeline

Fixes missing experience data for 1,000 candidate profiles by scraping LinkedIn via Apify, parsing durations, and storing in MongoDB.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set:
#   APIFY_API_KEY=your_key
#   APIFY_ACTOR_ID=GOvL4O4RwFqsdIqXF
#   MONGO_URI=...
python main.py --init-db
python main.py --load-csv
python main.py --dry-run   # First 10 candidates only
python main.py --run       # Full pipeline (requires paid Apify plan)
```

## Apify Cost

The pipeline uses actor `GOvL4O4RwFqsdIqXF` (apimaestro/linkedin-profile-batch-scraper-no-cookies-required). The free tier is limited to 10 profiles/day, so the full 1,000-candidate run requires a paid Apify plan.

- **Estimated cost:** ~$5 for 1,000 profiles
- **Batch size:** 100 URLs per Apify run
- **Early stop:** pipeline stops at 950 successful fixes to save credits

## API

```bash
python run_api.py
curl http://localhost:8000/api/saral/profile/{candidate_id}
```

Response shape matches the engine endpoint. The API returns the full profile including `experience`, `education`, `skills`, `featured`, `is_open_to_work`, `profile_pic`, `about`, `location`, etc. (fields not available from the scraper are returned as `null` or empty arrays).

Example response:

```json
{
  "status": "success",
  "profile": {
    "id": "...",
    "name": "...",
    "headline": "...",
    "about": "...",
    "location": "...",
    "current_company": "...",
    "current_role": "...",
    "total_experience_months": 27,
    "skills": [...],
    "linkedin_url": "...",
    "profile_pic": "...",
    "is_open_to_work": false,
    "experience": [
      {
        "company": {
          "company_name": "...",
          "company_id": "...",
          "company_linkedin_url": "...",
          "span_text": "1 yr",
          "span_months": 12,
          "min_start": "...",
          "max_end": "..."
        },
        "positions": [
          {
            "role": "...",
            "start_date": "...",
            "end_date": null,
            "is_current": true,
            "duration_text": "Jun 2025 - Present · 1 yrs",
            "duration_months": 12,
            "effective_end": "...",
            "job_type": "...",
            "location": null,
            "work_type": "On-site",
            "description": null,
            "skills_used": []
          }
        ]
      }
    ],
    "education": [...],
    "featured": {...}
  }
}
```

## Project Structure

```
saral_api/
├── src/
│   ├── config.py           # Settings (Apify actor, MongoDB, batch sizes)
│   ├── models/             # Motor client + Pydantic schemas
│   ├── scraper/            # Apify client + response parser
│   ├── pipeline/           # CSV loader + batch processor
│   ├── api/                # FastAPI routes
│   └── utils/              # Logger, date parser, duration calc, URL validator
├── tests/                  # pytest suite (47 tests)
├── main.py                 # CLI: --init-db, --load-csv, --run, --dry-run
└── run_api.py              # API server on port 8000
```

## Key Features

- **Batch scraping** — 100 URLs per Apify run, up to 1,000 supported by the actor
- **Early stop at 950** — stops once the assignment threshold is reached, saving credits
- **URL validation** — invalid/missing LinkedIn URLs are skipped before paying for Apify
- **Apify limit detection** — halts cleanly with a clear message when free tier or paid limits are hit
- **Async concurrency** — 10 concurrent Apify requests via semaphore
- **Exponential backoff retry** — 3 retries: 2s → 4s → 8s
- **Circuit breaker** — halts if failures exceed 50, preventing runaway credit burn
- **Per-position validation** — skips empty role+company, keeps valid positions in the same candidate
- **Engine-compatible schema** — nested `company → positions` with `duration_text`, `effective_end`, `span_text`, `span_months`, `total_experience_months`
- **Cache-based resume** — Apify responses cached to disk, surviving script restarts
- **Structured JSON logging** — per-candidate success/failure with reason in `data/logs/`
- **Consistent duration rule** — current roles always compute to today, never copy the engine's 0-month bug
