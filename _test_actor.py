import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def test():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient(timeout=60) as c:
        # Submit run
        payload = {"linkedinUrl": "https://www.linkedin.com/in/divyeshsarvaiya"}
        print(f"Submitting to actor {actor}...")
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=payload)
        print(f"Submit status: {r.status_code}")
        run_data = r.json()
        print(f"Run response keys: {list(run_data.keys())}")
        run_id = run_data.get("data", {}).get("id")
        print(f"Run ID: {run_id}")
        
        # Poll
        for i in range(60):
            await asyncio.sleep(5)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            r2_data = r2.json()
            status = r2_data.get("data", {}).get("status")
            print(f"  Poll {i+1}: status={status}")
            
            if status == "SUCCEEDED":
                ds_id = r2_data.get("data", {}).get("defaultDatasetId")
                print(f"  Dataset ID: {ds_id}")
                items_r = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json", headers=headers)
                items = items_r.json()
                print(f"  Items count: {len(items)}")
                if items:
                    print(f"  First item keys: {list(items[0].keys())}")
                    print(f"  Headline: {items[0].get('headline', 'N/A')}")
                    exp_keys = [k for k in items[0].keys() if any(w in k.lower() for w in ['exp','pos','job','work'])]
                    print(f"  Experience-related keys: {exp_keys}")
                else:
                    print("  NO ITEMS RETURNED")
                break
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                error_msg = r2_data.get("data", {}).get("errorMessage", "")
                print(f"  Run {status}: {error_msg[:200]}")
                break

asyncio.run(test())
