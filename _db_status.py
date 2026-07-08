import asyncio
from src.models import get_candidates_collection

async def reset():
    col = get_candidates_collection()
    r = await col.update_many(
        {"status": {"$ne": "pending"}},
        {"$set": {"status": "pending", "experiences": [], "headline": None, "failure_reason": None, "processed_at": None}}
    )
    print(f"Reset {r.modified_count} candidates back to pending")

    total = await col.count_documents({})
    pending = await col.count_documents({"status": "pending"})
    print(f"Total: {total}, Pending: {pending}")

asyncio.run(reset())
