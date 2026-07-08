import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")

async def get_data():
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"https://api.apify.com/v2/datasets/D9IwVs91fhFWzGqH5/items?format=json&token={key}")
        items = r.json()
        if items:
            item = items[0]
            print("Top-level keys:", list(item.keys()))
            for k, v in item.items():
                if isinstance(v, (str, int, float, bool, type(None))):
                    print(f"  {k}: {str(v)[:100]}")
                elif isinstance(v, list):
                    print(f"  {k}: list[{len(v)}] {str(v)[:200]}")
                elif isinstance(v, dict):
                    print(f"  {k}: dict {list(v.keys())[:10]}")
asyncio.run(get_data())
