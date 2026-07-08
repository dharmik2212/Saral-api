import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def verify():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    # Test 1: Can it handle 5 URLs in one run?
    urls = [
        "https://www.linkedin.com/in/divyeshsarvaiya",
        "https://www.linkedin.com/in/tanusharma21280",
        "https://www.linkedin.com/in/roshani-kurve-479689255",
        "https://www.linkedin.com/in/ayush-nimje-690196250",
        "https://www.linkedin.com/in/priya-singh-8052bb399",
    ]
    
    async with httpx.AsyncClient(timeout=60) as c:
        payload = {"startUrls": [{"url": u} for u in urls]}
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=payload)
        run_id = r.json().get("data", {}).get("id")
        print(f"Run {run_id} with {len(urls)} URLs")
        
        for i in range(60):
            await asyncio.sleep(5)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            st = r2.json().get("data", {}).get("status")
            if st != "RUNNING":
                ds_id = r2.json().get("data", {}).get("defaultDatasetId")
                if ds_id:
                    ir = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json", headers=headers)
                    items = ir.json()
                    print(f"Status={st}, items={len(items)}")
                    
                    if items:
                        for idx, item in enumerate(items):
                            print(f"\n--- Item {idx} ---")
                            print(f"  Top keys: {list(item.keys())}")
                            for k in ["headline", "name", "firstName", "lastName", "position", "title", "currentCompany"]:
                                if k in item:
                                    v = item[k]
                                    print(f"  {k}: {str(v)[:120]}")
                            for k in item:
                                if isinstance(item[k], list) and len(item[k]) > 0 and item[k] is not None:
                                    print(f"  {k}: list[{len(item[k])}]")
                                    if len(item[k]) > 0 and isinstance(item[k][0], dict):
                                        print(f"    first item keys: {list(item[k][0].keys())[:10]}")
                                elif isinstance(item[k], dict) and item[k] is not None:
                                    print(f"  {k}: dict {list(item[k].keys())[:10]}")
                break
            if i % 3 == 0:
                print(f"  poll {i+1}s: {st}")

asyncio.run(verify())
