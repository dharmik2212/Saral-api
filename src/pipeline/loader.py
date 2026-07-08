import pandas as pd
from pymongo import UpdateOne
from uuid import UUID
from src.models import get_candidates_collection
from src.config import get_settings


async def load_csv_to_db(csv_path: str = None) -> int:
    """Bulk load candidates from CSV to MongoDB. Returns count loaded."""
    settings = get_settings()
    csv_path = csv_path or settings.raw_csv
    df = pd.read_csv(csv_path)
    col = get_candidates_collection()
    loaded = 0
    bulk_ops = []

    for _, row in df.iterrows():
        doc = {
            "id": row["id"],
            "full_name": row["full_name"],
            "linkedin_url": row["linkedin_url"],
            "current_role": row.get("current_role") if pd.notna(row.get("current_role")) else None,
            "current_company": row.get("current_company") if pd.notna(row.get("current_company")) else None,
            "headline": None,
            "experiences": [],
            "issue": row.get("issue"),
            "created_at": row.get("created_at"),
            "processed_at": None,
            "status": "pending",
            "failure_reason": None,
        }
        bulk_ops.append(UpdateOne({"id": row["id"]}, {"$set": doc}, upsert=True))

        if len(bulk_ops) >= 250:
            result = await col.bulk_write(bulk_ops, ordered=False)
            loaded += result.upserted_count + result.modified_count
            bulk_ops = []

    if bulk_ops:
        result = await col.bulk_write(bulk_ops, ordered=False)
        loaded += result.upserted_count + result.modified_count

    return loaded


async def get_pending_candidates(limit: int = None) -> list[dict]:
    """Get all pending candidates from MongoDB."""
    col = get_candidates_collection()
    cursor = col.find({"status": "pending"})
    if limit:
        cursor = cursor.limit(limit)
    return await cursor.to_list(length=limit or 10000)


async def get_candidate_by_id(candidate_id: UUID) -> dict | None:
    """Get a single candidate by ID."""
    col = get_candidates_collection()
    return await col.find_one({"id": str(candidate_id)})
