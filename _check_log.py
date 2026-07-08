import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("APIFY_API_KEY")
actor = os.getenv("APIFY_ACTOR_ID")
run_id = "tof4gFuUkTeLW3Nrb"  # our test run

async def check():
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as c:
        # Get run log
        r = await c.get(f"https://api.apify.com/v2/actor-runs/{run_id}/log?token={key}")
        print("LOG:")
        print(r.text[-3000:])

asyncio.run(check())
