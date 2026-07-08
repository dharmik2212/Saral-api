import asyncio, httpx, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")

async def test():
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"https://api.apify.com/v2/acts/{actor}?token={key}")
        data = r.json()
        inp = data.get("data", {}).get("input", {})
        if inp:
            print("Input schema keys:", list(inp.keys()))
            print(json.dumps(inp, indent=2)[:2000])
        else:
            print("Raw:", json.dumps(data, indent=2)[:3000])

asyncio.run(test())
