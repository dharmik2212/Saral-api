import asyncio
from src.models import get_candidates_collection

async def check():
    col = get_candidates_collection()
    total = await col.count_documents({})
    pending = await col.count_documents({"status": "pending"})
    print(f"Total: {total}, Pending: {pending}")

asyncio.run(check())
