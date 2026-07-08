import asyncio, os, json
from dotenv import load_dotenv
load_dotenv()

from src.scraper.apify_client import ApifyClient

async def test():
    client = ApifyClient()
    url = "https://www.linkedin.com/in/divyeshsarvaiya"
    print(f"Testing individual fetch: {url} ...")
    data, error = await client.fetch_profile(url)
    if data:
        print("Got data!")
        print("Keys:", list(data.keys())[:15])
        exp_keys = [k for k in data.keys() if "exp" in k.lower() or "pos" in k.lower()]
        print("Experience keys:", exp_keys)
        headline = data.get("headline", data.get("title", "N/A"))
        print("Headline:", headline)
    else:
        print("Error:", error)

asyncio.run(test())
