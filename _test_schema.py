import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def get_input_schema():
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        # Try to get input schema
        r = await c.get(f"https://api.apify.com/v2/acts/{actor}/input-schema?token={key}")
        data = r.json()
        print("Input schema:")
        schema = data.get("data", data)
        print(json.dumps(schema, indent=2)[:3000])

        # Also try the actor API docs
        r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/last?token={key}&status=SUCCEEDED")
        d2 = r2.json()
        last_run = d2.get("data", {})
        if last_run:
            ds_id = last_run.get("defaultDatasetId")
            if ds_id:
                print(f"\nLast successful run dataset: {ds_id}")
                items_r = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?token={key}&limit=1")
                items = items_r.json()
                if items:
                    print("Sample item keys:", list(items[0].keys())[:20])

asyncio.run(get_input_schema())
