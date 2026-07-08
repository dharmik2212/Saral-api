import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = "GOvL4O4RwFqsdIqXF"  # apimaestro/linkedin-profile-batch-scraper-no-cookies-required

async def debug():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    usernames = [
        "https://www.linkedin.com/in/divyeshsarvaiya",
        "https://www.linkedin.com/in/tanusharma21280",
    ]

    async with httpx.AsyncClient(timeout=60) as c:
        payload = {"usernames": usernames}
        r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=payload)
        run_id = r.json().get("data", {}).get("id")
        print(f"Run {run_id}")

        for i in range(120):
            await asyncio.sleep(10)
            r2 = await c.get(f"https://api.apify.com/v2/acts/{actor}/runs/{run_id}", headers=headers)
            st = r2.json().get("data", {}).get("status")
            print(f"  {i*10}s: {st}")
            if st != "RUNNING":
                ds_id = r2.json().get("data", {}).get("defaultDatasetId")
                if ds_id and st == "SUCCEEDED":
                    ir = await c.get(f"https://api.apify.com/v2/datasets/{ds_id}/items?format=json", headers=headers)
                    items = ir.json()
                    print(f"\nItems: {len(items)}")
                    for idx, item in enumerate(items):
                        print(f"\n--- Item {idx} keys: {list(item.keys())}")
                        for k in item:
                            v = item[k]
                            if isinstance(v, (str, int, float, bool, type(None))):
                                print(f"  {k}: {str(v)[:200]}")
                            elif isinstance(v, list):
                                print(f"  {k}: list[{len(v)}]")
                                if v and isinstance(v[0], dict):
                                    print(f"    first keys: {list(v[0].keys())[:15]}")
                                    if "experience" in k.lower() or "position" in k.lower():
                                        for exp in v[:2]:
                                            print(f"    exp keys: {list(exp.keys())[:10]}")
                            elif isinstance(v, dict):
                                print(f"  {k}: dict keys={list(v.keys())[:10]}")
                elif st != "SUCCEEDED":
                    print(f"Run status: {st}")
                    err_info = r2.json().get("data", {}).get("error", {})
                    if err_info:
                        print(f"Error: {err_info}")
                else:
                    print("No dataset ID")

                log_r = await c.get(f"https://api.apify.com/v2/actor-runs/{run_id}/log?token={key}")
                print(f"\nLOG (last 1000 chars): {log_r.text[-1000:]}")
                break

asyncio.run(debug())
