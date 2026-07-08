import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")

# Try the Harvest API directly
async def test():
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as c:
        # Try Harvest API endpoint that this actor wraps
        r = await c.post(
            "http://apify-api-2.harvest-api.com/api/linkedin/profile",
            json={"linkedin_url": "https://www.linkedin.com/in/divyeshsarvaiya"},
            headers={"X-Harvest-Token": key}
        )
        print("Harvest direct:", r.status_code, r.text[:300] if r.text else "empty")

asyncio.run(test())
