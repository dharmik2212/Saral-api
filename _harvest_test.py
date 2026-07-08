import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def try_input_fields():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = "https://www.linkedin.com/in/divyeshsarvaiya"
    
    # Harvest API specific input fields
    payloads = [
        {"profileUrl": url}, {"profile_url": url},
        {"linkedin": url}, {"input": {"linkedin_url": url}},
        {"username": "divyeshsarvaiya"}, {"profileId": "divyeshsarvaiya"},
        {"handle": "divyeshsarvaiya"}, {"slug": "divyeshsarvaiya"},
    ]
    
    async with httpx.AsyncClient(timeout=60) as c:
        for p in payloads:
            r = await c.post(f"https://api.apify.com/v2/acts/{actor}/runs", headers=headers, json=p)
            run_id = r.json().get("data", {}).get("id")
            print(f"Input {list(p.keys())[0]:<15}: run={run_id}, status={r.status_code}")

asyncio.run(try_input_fields())
