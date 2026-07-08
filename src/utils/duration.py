from calendar import month_abbr
from datetime import date
from typing import Optional
from collections import defaultdict

from src.utils.date_parser import (
    parse_date, calc_months, is_current_role,
    generate_duration_text, effective_end_date
)


def _month_to_int(month: Optional[str]) -> int:
    """Convert month name, abbreviation, or digit to integer."""
    if month is None:
        return 1
    if isinstance(month, int):
        return month
    month = str(month).strip()
    if month.isdigit():
        return int(month)
    # Try month abbreviation (e.g., "Mar") or full name (e.g., "March")
    for idx, name in enumerate(month_abbr):
        if name and month.lower() in (name.lower(), name.lower()[:3]):
            return idx
    return 1


def _dict_date_to_str(d: dict) -> Optional[str]:
    """Convert {'year': 2022, 'month': 'Mar'} or {'year': 2022} to 'Mar 2022'."""
    if not d:
        return None
    year = d.get("year")
    if not year:
        return None
    month = _month_to_int(d.get("month"))
    return date(year, month, 1).strftime("%b %Y")


def parse_position(pos: dict) -> Optional[dict]:
    """
    Parse a single position dict from Apify raw data.
    Returns None if the position should be skipped (empty role AND empty company).
    """
    role = (
        pos.get("title") or pos.get("position") or pos.get("jobTitle") or ""
    ).strip()

    company_name = (
        pos.get("companyName") or pos.get("company") or
        pos.get("organization") or pos.get("organisation") or ""
    ).strip()

    if not role and not company_name:
        return None

    start_str = pos.get("startDate") or pos.get("start_date") or pos.get("start")
    end_str = pos.get("endDate") or pos.get("end_date") or pos.get("end")

    if isinstance(start_str, dict):
        start_str = _dict_date_to_str(start_str)
    if isinstance(end_str, dict):
        end_str = _dict_date_to_str(end_str)

    if "is_current" in pos and isinstance(pos["is_current"], bool):
        is_current = pos["is_current"]
    else:
        is_current = is_current_role(end_str)
    start_date = parse_date(start_str) if start_str else None
    end_date = None if is_current else (parse_date(end_str) if end_str else None)

    duration_months = None
    if start_date:
        duration_months = calc_months(start_date, None if is_current else end_date)

    duration_text = generate_duration_text(start_date, end_date, is_current, duration_months)
    effective_end = effective_end_date(end_date, is_current)

    company_id = pos.get("companyId") or pos.get("company_id")
    company_linkedin_url = pos.get("companyLinkedinUrl") or pos.get("company_linkedin_url") or pos.get("companyUrl")
    company_image_url = pos.get("companyLogo") or pos.get("company_logo_url") or pos.get("companyImageUrl") or pos.get("company_image_url")

    resolve_url = pos.get("companyUrn") or pos.get("companyLinkedInId")
    if resolve_url and not company_linkedin_url:
        if resolve_url.startswith("urn:li:company:"):
            numeric_id = resolve_url.replace("urn:li:company:", "")
            company_linkedin_url = f"https://www.linkedin.com/company/{numeric_id}/"

    job_type = pos.get("jobType") or pos.get("employmentType") or pos.get("job_type")
    location = pos.get("location") or pos.get("locationName") or pos.get("location_name")
    work_type = pos.get("workType") or pos.get("remoteWorking") or pos.get("work_type")
    description = pos.get("description")
    skills_used = pos.get("skillsUsed") or pos.get("skills") or pos.get("skills_used") or []

    if isinstance(skills_used, str):
        skills_used = [skills_used]

    return {
        "role": role,
        "company_name": company_name,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "is_current": is_current,
        "duration_text": duration_text,
        "duration_months": duration_months,
        "effective_end": effective_end,
        "job_type": job_type,
        "location": location,
        "work_type": work_type,
        "description": description,
        "skills_used": skills_used,
        "company_id": str(company_id) if company_id else None,
        "company_linkedin_url": company_linkedin_url,
        "company_image_url": company_image_url,
    }


def build_experiences(positions_meta: list[dict]) -> list[dict]:
    """
    Group positions by company name (case-insensitive) and build engine-compatible experience entries.
    Each entry = one company with all positions grouped under it.
    """
    grouped = defaultdict(list)

    for pos in positions_meta:
        key = pos.get("company_name", "").strip().lower()
        grouped[key].append(pos)

    experiences = []

    for company_key, positions in grouped.items():
        if not positions:
            continue

        first = positions[0]
        company_name = first["company_name"]

        company_meta = {
            "company_name": company_name,
            "company_id": first.get("company_id"),
            "company_linkedin_url": first.get("company_linkedin_url"),
            "company_image_url": first.get("company_image_url"),
            "s3_company_logo": None,
        }

        all_starts = []
        all_ends = []

        clean_positions = []
        for pos in positions:
            start_d = parse_date(pos.get("start_date"))
            end_d = None if pos.get("is_current") else parse_date(pos.get("end_date"))

            if start_d:
                all_starts.append(start_d)
            if not pos.get("is_current") and end_d:
                all_ends.append(end_d)
            elif pos.get("is_current"):
                all_ends.append(date.today())

            clean_positions.append({
                "role": pos["role"],
                "start_date": pos.get("start_date"),
                "end_date": pos.get("end_date"),
                "is_current": pos.get("is_current", False),
                "duration_text": pos.get("duration_text"),
                "duration_months": pos.get("duration_months"),
                "effective_end": pos.get("effective_end"),
                "job_type": pos.get("job_type"),
                "location": pos.get("location"),
                "work_type": pos.get("work_type"),
                "description": pos.get("description"),
                "skills_used": pos.get("skills_used", []),
            })

        min_start = min(all_starts).isoformat() if all_starts else None
        max_end = max(all_ends).isoformat() if all_ends else None

        span_months = None
        if all_starts and all_ends:
            span_months = calc_months(min(all_starts), max(all_ends))

        span_text = None
        if all_starts:
            start_fmt = format_month_year(min(all_starts))
            if any(pos.get("is_current") for pos in positions):
                end_fmt = "Present"
            elif all_ends:
                end_fmt = format_month_year(max(all_ends))
            else:
                end_fmt = "Present"

            if span_months is not None:
                yrs = span_months // 12
                mos = span_months % 12
                parts = []
                if yrs > 0:
                    parts.append(f"{yrs} yr{'s' if yrs != 1 else ''}")
                if mos > 0:
                    parts.append(f"{mos} mo{'s' if mos != 1 else ''}")
                if not parts:
                    parts.append("0 mos")
                dur_str = " ".join(parts)
                span_text = f"{start_fmt} - {end_fmt} · {dur_str}"
            else:
                span_text = f"{start_fmt} - {end_fmt}"

        company_meta["min_start"] = min_start
        company_meta["max_end"] = max_end
        company_meta["span_text"] = span_text
        company_meta["span_months"] = span_months

        experiences.append({
            "company": company_meta,
            "positions": clean_positions,
        })

    return experiences


def compute_total_experience_months(experiences: list[dict]) -> int:
    """Sum duration_months across all positions in all company groups."""
    total = 0
    for exp in experiences:
        for pos in exp.get("positions", []):
            months = pos.get("duration_months")
            if months is not None:
                total += months
    return total


def format_month_year(d: date) -> str:
    return d.strftime("%b %Y")


def parse_experiences(raw_data: dict) -> list[dict]:
    """
    Top-level entry: parse Apify raw data into engine-compatible experience format.
    Handles both flat position lists and pre-grouped company→positions structures.
    Returns empty list for genuinely empty profiles (no positions found).
    """
    positions_meta = []

    positions_raw = (
        raw_data.get("positions") or
        raw_data.get("experience") or
        raw_data.get("experiences") or
        []
    )

    for item in positions_raw:
        if isinstance(item, dict) and "positions" in item:
            company_wrapper = item.get("company", {})
            company_name = (
                company_wrapper.get("companyName") or
                company_wrapper.get("company_name") or
                company_wrapper.get("name") or
                ""
            )
            company_id = company_wrapper.get("companyId") or company_wrapper.get("company_id")
            company_linkedin_url = company_wrapper.get("companyLinkedinUrl") or company_wrapper.get("company_linkedin_url")
            company_image_url = company_wrapper.get("companyLogo") or company_wrapper.get("company_logo_url") or company_wrapper.get("companyImageUrl")

            for pos in item.get("positions", []):
                role = (
                    pos.get("title") or pos.get("role") or pos.get("jobTitle") or ""
                ).strip()
                if not role and not company_name:
                    continue

                start_str = pos.get("startDate") or pos.get("start_date")
                end_str = pos.get("endDate") or pos.get("end_date")

                if isinstance(start_str, dict):
                    start_str = _dict_date_to_str(start_str)
                if isinstance(end_str, dict):
                    end_str = _dict_date_to_str(end_str)

                if "is_current" in pos and isinstance(pos["is_current"], bool):
                    is_current = pos["is_current"]
                else:
                    is_current = is_current_role(end_str)
                start_date = parse_date(start_str) if start_str else None
                end_date = None if is_current else (parse_date(end_str) if end_str else None)
                duration_months = calc_months(start_date, None if is_current else end_date) if start_date else None
                duration_text = generate_duration_text(start_date, end_date, is_current, duration_months)
                effective_end = effective_end_date(end_date, is_current)

                positions_meta.append({
                    "role": role,
                    "company_name": company_name,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "is_current": is_current,
                    "duration_text": duration_text,
                    "duration_months": duration_months,
                    "effective_end": effective_end,
                    "job_type": pos.get("jobType") or pos.get("employmentType"),
                    "location": pos.get("location") or pos.get("locationName"),
                    "work_type": pos.get("workType") or pos.get("remoteWorking"),
                    "description": pos.get("description"),
                    "skills_used": pos.get("skillsUsed") or pos.get("skills") or [],
                    "company_id": str(company_id) if company_id else None,
                    "company_linkedin_url": company_linkedin_url,
                    "company_image_url": company_image_url,
                })
        else:
            parsed = parse_position(item)
            if parsed is not None:
                positions_meta.append(parsed)

    return build_experiences(positions_meta)
