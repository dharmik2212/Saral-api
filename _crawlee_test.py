import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def test():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = "https://www.linkedin.com/in/divyeshsarvaiya"
    
    # Crawlee standard format + get log
    payload = {
        "startUrls": [{"url": url, "method": "GET"}],
        "maxItems": 1
    }
    
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=payload)
        run_id = r.json().get("data", {}).get("id")
        print(f"Run {run_id} started with Crawlee format")
        
        for i in range(30):
            await asyncio.sleep(5)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            st = r2.json().get("data", {}).get("status")
            if st != "RUNNING":
                ds_id = r2.json().get("data", {}).get("defaultDatasetId")
                items = 0
                if ds_id:
                    iris = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json", headers=headers)
                    items = len(iris.json())
                print(f"  {st}, ds={ds_id}, items={items}")
                
                # Get log
                log_r = await c.get(f"https://api.apify.com/v2/actor-runs/{run_id}/log?token={key}")
                print("LOG (last 2000 chars):")
                print(log_r.text[-2000:])
                break
            print(f"  poll {i+1}: {st}")

asyncio.run(test())
