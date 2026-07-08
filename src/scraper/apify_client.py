import asyncio
import httpx
import json
from typing import Optional
from pathlib import Path
from datetime import datetime
import aiofiles

from src.config import get_settings


class ApifyClient:
    """Async client for Apify LinkedIn scraper with batch+individual retry logic."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.apify_api_key
        self.actor_id = settings.apify_actor_id
        self.max_retries = settings.max_retries
        self.max_concurrent = settings.max_concurrent
        self.batch_urls_per_run = settings.batch_urls_per_run
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _get_cache_path(self, url: str) -> Path:
        safe_name = url.split("/in/")[-1].replace("/", "_").replace("?", "_")
        return self.cache_dir / f"{safe_name}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return data.get("status") == "success"
        except (json.JSONDecodeError, IOError):
            return False

    async def fetch_profile(self, linkedin_url: str) -> tuple[Optional[dict], Optional[str]]:
        """Fetch a SINGLE LinkedIn profile from Apify (used as fallback)."""
        cache_path = self._get_cache_path(linkedin_url)
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    return data.get("data"), None
            except (json.JSONDecodeError, IOError):
                pass

        async with self.semaphore:
            for attempt in range(self.max_retries):
                try:
                    result = await self._submit_and_wait({"usernames": [linkedin_url]})

                    if result.get("status") == "success":
                        items = result.get("data", [])
                        item = items[0] if items else None

                        await self._cache_result(cache_path, {
                            "status": "success" if item else "error",
                            "data": item,
                            "error": None if item else {"type": "empty_response"},
                            "cached_at": datetime.utcnow().isoformat(),
                        })
                        return item, None if item else "empty_response"

                    error_type = result.get("error", {}).get("type", "unknown")
                    if error_type in ["404", "private_profile", "invalid_url"]:
                        return None, f"Apify {error_type}"
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None, f"Apify {error_type}"

                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None, "Apify Timeout"
                except httpx.HTTPStatusError as e:
                    msg = self._http_error_msg(e)
                    if e.response.status_code == 429 and attempt < self.max_retries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    return None, msg
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None, f"Request Error: {str(e)}"

        return None, "Max retries exceeded"

    async def fetch_profiles_batch(self, linkedin_urls: list[str]) -> dict[str, Optional[dict]]:
        """
        Send URLs in a single Apify run using usernames input format.
        Max 1000 usernames per run.
        """
        if not linkedin_urls:
            return {}

        uncached_urls = []
        results = {}

        for url in linkedin_urls:
            cache_path = self._get_cache_path(url)
            if self._is_cache_valid(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        data = json.load(f)
                        results[url] = data.get("data")
                except (json.JSONDecodeError, IOError):
                    uncached_urls.append(url)
            else:
                uncached_urls.append(url)

        if not uncached_urls:
            return results

        # Build usernames payload for batch scraper
        async with self.semaphore:
            result = await self._submit_and_wait({"usernames": uncached_urls})
            items = result.get("data", []) if result.get("status") == "success" else []

            error_items = [it for it in items if "error" in it and len(it) == 1]
            if error_items and len(error_items) == len(items):
                error_msg = error_items[0]["error"]
                raise RuntimeError(f"Apify actor returned error for all URLs: {error_msg}")

            # Detect actor-level free-tier / limit messages
            limit_items = [
                it for it in items
                if it.get("message") and any(
                    phrase in it["message"].lower()
                    for phrase in ["free-tier", "free tier", "limited to", "upgrade your apify plan", "wait until tomorrow"]
                )
            ]
            if limit_items:
                raise RuntimeError(f"Apify limit reached: {limit_items[0].get('message')}")

            url_to_item = {}
            for item in items:
                    raw_url = (
                        item.get("profileUrl") or item.get("linkedinUrl") or
                        item.get("url") or item.get("linkedInUrl") or ""
                    )
                    if isinstance(raw_url, list):
                        raw_url = raw_url[0] if raw_url else ""
                    item_url = str(raw_url).rstrip("/")
                    if item_url:
                        norm_item_url = item_url.replace("https://www.", "https://").replace("http://www.", "http://")
                        url_to_item[norm_item_url] = item
                        for orig in uncached_urls:
                            norm_orig = orig.rstrip("/").replace("https://www.", "https://").replace("http://www.", "http://")
                            if norm_orig == norm_item_url:
                                url_to_item[orig] = item

            for url in uncached_urls:
                norm_url = url.replace("https://www.", "https://").replace("http://www.", "http://")
                item = url_to_item.get(norm_url) or url_to_item.get(norm_url.rstrip("/"))
                results[url] = item
                cache_path = self._get_cache_path(url)
                await self._cache_result(cache_path, {
                    "status": "success" if item else "error",
                    "data": item,
                    "error": None if item else {"type": "not_in_response"},
                    "cached_at": datetime.utcnow().isoformat(),
                })

            return results

    async def _fallback_individual(self, urls: list[str]) -> dict[str, Optional[dict]]:
        """If batch input fails, fetch one by one."""
        results = {}
        tasks = [self.fetch_profile(url) for url in urls]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(urls, gathered):
            if isinstance(result, Exception):
                results[url] = None
            else:
                data, _ = result
                results[url] = data
        return results

    async def _submit_and_wait(self, input_payload: dict) -> dict:
        """Submit a run to Apify and poll until completion, then return dataset items."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api.apify.com/v2/acts/{self.actor_id}/runs",
                headers=headers,
                json=input_payload,
            )
            response.raise_for_status()
            run_data = response.json()
            run_id = run_data.get("data", {}).get("id")

            return await self._wait_for_run(client, run_id, headers)

    async def _wait_for_run(self, client: httpx.AsyncClient, run_id: str, headers: dict, max_wait: int = 600) -> dict:
        """Poll Apify until run completes. Max wait increased to 10 min for batches."""
        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < max_wait:
            response = await client.get(
                f"https://api.apify.com/v2/acts/{self.actor_id}/runs/{run_id}",
                headers=headers,
            )
            response.raise_for_status()
            run_info = response.json()
            status = run_info.get("data", {}).get("status")

            if status == "SUCCEEDED":
                dataset_id = run_info.get("data", {}).get("defaultDatasetId")
                return await self._get_dataset_items(client, dataset_id, headers)
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                return {"status": "error", "error": {"type": status.lower()}}

            await asyncio.sleep(10)

        return {"status": "error", "error": {"type": "timeout"}}

    async def _get_dataset_items(self, client: httpx.AsyncClient, dataset_id: str, headers: dict) -> dict:
        """Get all items from Apify dataset."""
        response = await client.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json&clean=true",
            headers=headers,
        )
        response.raise_for_status()
        items = response.json()
        return {"status": "success", "data": items if isinstance(items, list) else [items]}

    async def _cache_result(self, cache_path: Path, result: dict):
        result["cached_at"] = datetime.utcnow().isoformat()
        async with aiofiles.open(cache_path, 'w') as f:
            await f.write(json.dumps(result))

    @staticmethod
    def _http_error_msg(e: httpx.HTTPStatusError) -> str:
        if e.response.status_code == 404:
            return "HTTP 404"
        elif e.response.status_code == 403:
            return "Private Profile (403)"
        return f"HTTP {e.response.status_code}"
