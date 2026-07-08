import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID
from urllib.parse import urlparse
import re

from src.models import get_candidates_collection
from src.scraper import ApifyClient
from src.scraper.parser import parse_profile
from src.utils.logger import setup_logger, log_success, log_failure, log_circuit_breaker
from src.config import get_settings


def _validate_linkedin_url(url: str) -> Optional[str]:
    """Validate a LinkedIn URL. Returns error message if invalid, None if valid."""
    if not url or not isinstance(url, str):
        return "Missing or invalid LinkedIn URL"
    url = url.strip()
    if not url:
        return "Empty LinkedIn URL"
    try:
        parsed = urlparse(url)
    except Exception:
        return "Malformed LinkedIn URL"
    if parsed.scheme not in ("http", "https"):
        return "Invalid URL scheme"
    netloc = parsed.netloc.lower()
    if netloc not in ("linkedin.com", "www.linkedin.com"):
        return "Not a LinkedIn URL"
    if not re.match(r"^/in/[^/]+/?$", parsed.path, re.IGNORECASE):
        return "Missing /in/ profile path"
    return None


class PipelineProcessor:
    """Main pipeline orchestrator with batch Apify calls + circuit breaker."""

    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger()
        self.scraper = ApifyClient()
        self.col = get_candidates_collection()

        self.success_count = 0
        self.failure_count = 0
        self.success_threshold = 950
        self.failure_limit = 50
        self.halted = False

    def _check_circuit_breaker(self):
        if self.failure_count >= self.failure_limit:
            log_circuit_breaker(self.logger, self.failure_count, self.success_count)
            self.halted = True
            return True
        return False

    async def _update_candidate(
        self,
        candidate_id: str,
        profile: dict,
        status: str,
        failure_reason: Optional[str] = None,
    ):
        set_fields = {
            "status": status,
            "failure_reason": failure_reason,
            "processed_at": datetime.utcnow(),
        }
        if profile:
            set_fields.update({
                "headline": profile.get("headline"),
                "name": profile.get("name"),
                "about": profile.get("about"),
                "location": profile.get("location"),
                "location_city": profile.get("location_city"),
                "location_state": profile.get("location_state"),
                "location_country": profile.get("location_country"),
                "current_company": profile.get("current_company"),
                "current_role": profile.get("current_role"),
                "work_mode": profile.get("work_mode"),
                "total_experience_months": profile.get("total_experience_months", 0),
                "skills": profile.get("skills", []),
                "experiences": profile.get("experience", []),
                "education": profile.get("education", []),
                "featured": profile.get("featured"),
                "is_open_to_work": profile.get("is_open_to_work", False),
                "linkedin_url": profile.get("linkedin_url"),
                "github_url": profile.get("github_url"),
                "linkedin_username": profile.get("linkedin_username"),
                "github_username": profile.get("github_username"),
                "social_urls": profile.get("social_urls", {}),
                "profile_pic": profile.get("profile_pic"),
                "emails": profile.get("emails", []),
                "phonenumbers": profile.get("phonenumbers", []),
                "followers": profile.get("followers"),
                "gender": profile.get("gender"),
                "tier": profile.get("tier"),
                "seniority_level": profile.get("seniority_level"),
                "primary_domain": profile.get("primary_domain"),
                "normalized_skills": profile.get("normalized_skills"),
                "source": profile.get("source"),
                "last_scored_at": profile.get("last_scored_at"),
                "created_at": profile.get("created_at"),
                "updated_at": profile.get("updated_at"),
                "enriched_at": profile.get("enriched_at"),
            })

        await self.col.update_one(
            {"id": candidate_id},
            {"$set": set_fields}
        )

    async def process_candidate(self, candidate: dict, raw_data: Optional[dict], error: Optional[str]) -> bool:
        """Process a single candidate from pre-fetched data."""
        try:
            profile, parse_error = parse_profile(raw_data, error)

            if parse_error:
                self.failure_count += 1
                await self._update_candidate(candidate["id"], {}, "failed", parse_error)
                log_failure(self.logger, candidate["id"], parse_error)
                self._check_circuit_breaker()
                return False

            self.success_count += 1
            await self._update_candidate(
                candidate["id"], profile, "success"
            )
            log_success(self.logger, candidate["id"], {
                "experience_count": len(profile.get("experience", [])),
                "total_experience_months": profile.get("total_experience_months", 0),
            })
            return True

        except Exception as e:
            self.failure_count += 1
            error_msg = str(e)
            await self._update_candidate(candidate["id"], {}, "failed", error_msg)
            log_failure(self.logger, candidate["id"], error_msg)
            self._check_circuit_breaker()
            return False

    async def process_batch(self, candidates: list[dict], results: dict[str, Optional[dict]]) -> tuple[int, int]:
        tasks = []
        for candidate in candidates:
            url = candidate["linkedin_url"]
            if url in results:
                raw_data = results[url]
                error = None if raw_data is not None else "profile not returned by batch"
            else:
                raw_data, error = None, "profile not in batch response"
            tasks.append(self.process_candidate(candidate, raw_data, error))

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        batch_success = sum(1 for r in gathered if r is True)
        batch_failure = sum(1 for r in gathered if r is False)
        return batch_success, batch_failure

    async def run(self, dry_run: bool = False):
        from src.pipeline.loader import get_pending_candidates

        self.logger.info("Starting pipeline (batch mode)...")

        candidates = await get_pending_candidates()
        self.logger.info(f"Found {len(candidates)} pending candidates")

        if dry_run:
            self.logger.info("DRY RUN - Processing first 10 candidates only")
            candidates = candidates[:10]

        urls_per_batch = self.settings.batch_urls_per_run

        for chunk_start in range(0, len(candidates), urls_per_batch):
            if self.halted:
                self.logger.warning("Pipeline halted due to circuit breaker")
                break

            if self.success_count >= self.success_threshold:
                self.logger.info(
                    f"Success threshold {self.success_threshold} already reached."
                )
                break

            chunk_end = min(chunk_start + urls_per_batch, len(candidates))
            chunk = candidates[chunk_start:chunk_end]

            # Validate URLs before paying for Apify
            valid_chunk = []
            for candidate in chunk:
                url = candidate["linkedin_url"]
                error = _validate_linkedin_url(url)
                if error:
                    self.failure_count += 1
                    await self._update_candidate(candidate["id"], {}, "failed", error)
                    log_failure(self.logger, candidate["id"], error)
                    self._check_circuit_breaker()
                else:
                    valid_chunk.append(candidate)

            if not valid_chunk:
                continue

            urls = [c["linkedin_url"] for c in valid_chunk]

            chunk_num = chunk_start // urls_per_batch + 1
            total_chunks = (len(candidates) + urls_per_batch - 1) // urls_per_batch
            self.logger.info(f"Fetching chunk {chunk_num}/{total_chunks} ({len(urls)} URLs in 1 Apify run)")

            try:
                results = await self.scraper.fetch_profiles_batch(urls)
            except RuntimeError as e:
                self.logger.critical(f"Apify batch fetch failed: {e}")
                self.halted = True
                break
            got = sum(1 for v in results.values() if v is not None)
            self.logger.info(f"Chunk fetch complete: {got}/{len(urls)} returned data")

            db_batch_size = self.settings.batch_size
            for db_start in range(0, len(valid_chunk), db_batch_size):
                db_end = min(db_start + db_batch_size, len(valid_chunk))
                db_chunk = valid_chunk[db_start:db_end]

                success, failure = await self.process_batch(db_chunk, results)
                self.logger.info(
                    f"DB write: {success} success, {failure} failures. "
                    f"Total: {self.success_count} success, {self.failure_count} failures"
                )

                if self._check_circuit_breaker():
                    break

                if self.success_count >= self.success_threshold:
                    self.logger.info(
                        f"Success threshold {self.success_threshold} reached. Stopping early."
                    )
                    self.halted = True
                    break

        self.logger.info(f"Pipeline complete. Final: {self.success_count} success, {self.failure_count} failures")

        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "halted": self.halted,
            "threshold_met": self.success_count >= self.success_threshold,
        }


async def run_pipeline(dry_run: bool = False) -> dict:
    processor = PipelineProcessor()
    return await processor.run(dry_run=dry_run)
