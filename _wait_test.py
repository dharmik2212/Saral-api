import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def test():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = "https://www.linkedin.com/in/divyeshsarvaiya"

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json={"linkedinUrl": url})
        run_id = r.json().get("data", {}).get("id")
        print(f"Run: {run_id}, waiting...")

        for i in range(60):
            await asyncio.sleep(10)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            d2 = r2.json()
            st = d2.get("data", {}).get("status")
            print(f"  {i*10}s: {st}")
            if st == "SUCCEEDED":
                ds_id = d2.get("data", {}).get("defaultDatasetId")
                if ds_id:
                    ir = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json", headers=headers)
                    items = ir.json()
                    print(f"  Items: {len(items)}")
                    if items:
                        print(f"  Keys: {list(items[0].keys())}")
                        print(f"  Headline: {items[0].get('headline', 'N/A')}")
                break
            elif st in ["FAILED", "ABORTED", "TIMED-OUT"]:
                err = d2.get("data", {}).get("statusMessage", "")
                print(f"  {st}: {err[:300]}")
                break

asyncio.run(test())
