import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def try_formats():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = "https://www.linkedin.com/in/divyeshsarvaiya"
    
    formats = [
        {"linkedinUrl": url},
        {"profileUrl": url},
        {"linkedInUrl": url},
        {"profileUrls": [url]},
        {"startUrls": [{"url": url}]},
        {"url": url},
        {"urls": [url]},
        {"linkedinUrls": [url]},
    ]
    
    async with httpx.AsyncClient(timeout=15) as c:
        for payload in formats:
            try:
                r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=payload)
                run_id = r.json().get("data", {}).get("id")
                print(f"Payload {json.dumps(payload)[:60]:<65} -> status={r.status_code}, run_id={run_id}")
                if run_id:
                    await asyncio.sleep(2)
                    r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
                    st = r2.json().get("data", {}).get("status")
                    ds = r2.json().get("data", {}).get("defaultDatasetId")
                    items_count = 0
                    if ds:
                        ir = await c.get(f"https://api.apify.com/v2/datasets/{ds}/items?format=json", headers=headers)
                        items_count = len(ir.json())
                    print(f"  -> status={st}, items={items_count}")
            except Exception as e:
                print(f"  -> Error: {e}")

asyncio.run(try_formats())
