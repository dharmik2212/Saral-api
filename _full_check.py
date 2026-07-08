import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def full_check():
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as c:
        # Get a fresh run
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers={**headers, "Content-Type": "application/json"}, json={"linkedinUrl": "https://www.linkedin.com/in/divyeshsarvaiya"})
        run_id = r.json().get("data", {}).get("id")
        print(f"Run: {run_id}")
        
        # Wait for completion
        for i in range(30):
            await asyncio.sleep(4)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            st = r2.json().get("data", {}).get("status")
            if st == "SUCCEEDED":
                break
            elif st == "FAILED":
                print("FAILED:", r2.json().get("data", {}).get("statusMessage", "no msg"))
                break
        
        # Get log
        log_r = await c.get(f"https://api.apify.com/v2/actor-runs/{run_id}/log?token={key}")
        print("\nFULL LOG:")
        print(log_r.text)

        # Get dataset
        ds_id = r2.json().get("data", {}).get("defaultDatasetId")
        if ds_id:
            items_r = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json&limit=5", headers=headers)
            print(f"\nDATASET ({ds_id}) items count:", len(items_r.json()))
            if items_r.json():
                print("First item:", {k: str(v)[:80] for k, v in list(items_r.json()[0].items())[:15]})
        
        # Try output
        output_r = await c.get(f"https://api.apify.com/v2/actor-runs/{run_id}/output?token={key}", headers=headers)
        print(f"\nOUTPUT endpoint status: {output_r.status_code}")

asyncio.run(full_check())
