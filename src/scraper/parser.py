from typing import Optional

from src.utils.duration import parse_experiences, compute_total_experience_months


def extract_headline(raw_data: dict) -> Optional[str]:
    """Extract LinkedIn headline from raw Apify response."""
    basic_info = raw_data.get("basic_info", {})
    return (
        basic_info.get("headline") or
        raw_data.get("headline") or
        raw_data.get("tagline") or
        raw_data.get("description") or
        raw_data.get("summary")
    )


def extract_name(raw_data: dict) -> Optional[str]:
    basic_info = raw_data.get("basic_info", {})
    return basic_info.get("fullname") or raw_data.get("name")


def extract_about(raw_data: dict) -> Optional[str]:
    basic_info = raw_data.get("basic_info", {})
    return basic_info.get("about") or raw_data.get("about")


def extract_location(raw_data: dict) -> dict:
    basic_info = raw_data.get("basic_info", {})
    loc = basic_info.get("location") or raw_data.get("location") or {}
    if isinstance(loc, str):
        return {"full": loc, "city": None, "state": None, "country": None}
    return {
        "full": loc.get("full"),
        "city": loc.get("city"),
        "state": loc.get("state"),
        "country": loc.get("country"),
    }


def extract_skills(raw_data: dict) -> list[str]:
    skills = []
    basic_info = raw_data.get("basic_info", {})
    top_skills = basic_info.get("top_skills") or raw_data.get("skills") or []
    if isinstance(top_skills, list):
        for skill in top_skills:
            if isinstance(skill, str):
                skills.append(skill)
            elif isinstance(skill, dict) and skill.get("name"):
                skills.append(skill["name"])
    return skills


def extract_education(raw_data: dict) -> list[dict]:
    education_raw = raw_data.get("education") or []
    if not isinstance(education_raw, list):
        return []

    education = []
    for edu in education_raw:
        if not isinstance(edu, dict):
            continue
        start = edu.get("start_date")
        end = edu.get("end_date")
        education.append({
            "degree": edu.get("degree"),
            "degree_name": edu.get("degree_name"),
            "field_of_study": edu.get("field_of_study"),
            "school_name": edu.get("school"),
            "school_id": str(edu.get("school_id")) if edu.get("school_id") else None,
            "school_linkedin_url": edu.get("school_linkedin_url"),
            "school_logo": edu.get("school_logo_url") or edu.get("school_logo"),
            "s3_school_logo": None,
            "start_date": _date_to_str(start),
            "end_date": _date_to_str(end),
            "period": edu.get("duration"),
            "description": edu.get("description"),
        })
    return education


def extract_featured(raw_data: dict) -> Optional[dict]:
    featured_raw = raw_data.get("featured")
    if not featured_raw:
        return None
    if isinstance(featured_raw, list):
        if not featured_raw:
            return None
        featured_raw = featured_raw[0]
    if not isinstance(featured_raw, dict):
        return None

    return {
        "link": featured_raw.get("link") or featured_raw.get("url"),
        "title": featured_raw.get("title"),
        "description": featured_raw.get("description"),
        "url": featured_raw.get("url"),
        "image_url": featured_raw.get("image_url") or featured_raw.get("image"),
        "images": featured_raw.get("images") if isinstance(featured_raw.get("images"), list) else [],
        "slides": featured_raw.get("slides") if isinstance(featured_raw.get("slides"), list) else [],
        "subtitle": featured_raw.get("subtitle"),
    }


def _date_to_str(d) -> Optional[str]:
    """Convert date dict or string to a consistent string."""
    if not d:
        return None
    if isinstance(d, str):
        return d
    if isinstance(d, dict):
        year = d.get("year")
        month = d.get("month")
        if not year:
            return None
        if month:
            return f"{month} {year}"
        return str(year)
    return str(d)


def _current_role(experiences: list[dict]) -> Optional[str]:
    """Extract current role from parsed experiences."""
    for exp in experiences:
        for pos in exp.get("positions", []):
            if pos.get("is_current"):
                return pos.get("role")
    return None


def is_profile_genuinely_blank(data: dict) -> bool:
    """
    Determine if profile is genuinely blank or scraper failed.
    Returns True if profile has no experience data AND this is not a scraper error.
    """
    if not data:
        return True

    if data.get("error") or data.get("status") == "error":
        return False

    has_experiences = any(
        key in data
        for key in ["experiences", "experience", "workExperiences", "positions"]
    )

    if not has_experiences:
        return True

    experiences = (
        data.get("experiences") or
        data.get("experience") or
        data.get("workExperiences") or
        data.get("positions") or
        []
    )

    return len(experiences) == 0


def parse_profile(raw_data: Optional[dict], error: Optional[str]) -> tuple[dict, Optional[str]]:
    """
    Parse raw Apify response into a profile dict and error.

    Returns:
        Tuple of (profile_dict, failure_reason)
    """
    if error:
        return {}, error

    if not raw_data:
        return {}, "Empty response from Apify"

    if is_profile_genuinely_blank(raw_data):
        return {
            "headline": extract_headline(raw_data),
            "name": extract_name(raw_data),
            "about": extract_about(raw_data),
            "linkedin_url": raw_data.get("profileUrl") or raw_data.get("profile_url"),
        }, None

    try:
        location = extract_location(raw_data)
        experiences = parse_experiences(raw_data)
        total_months = compute_total_experience_months(experiences)
        basic_info = raw_data.get("basic_info", {})

        profile = {
            "headline": extract_headline(raw_data),
            "name": extract_name(raw_data),
            "about": extract_about(raw_data),
            "location": location.get("full"),
            "location_city": location.get("city"),
            "location_state": location.get("state"),
            "location_country": location.get("country"),
            "current_company": basic_info.get("current_company") or raw_data.get("current_company"),
            "current_role": _current_role(experiences),
            "work_mode": None,
            "total_experience_months": total_months,
            "skills": extract_skills(raw_data),
            "experience": experiences,
            "education": extract_education(raw_data),
            "featured": extract_featured(raw_data),
            "is_open_to_work": basic_info.get("open_to_work", False),
            "linkedin_url": raw_data.get("profileUrl") or basic_info.get("profile_url") or raw_data.get("url"),
            "github_url": None,
            "linkedin_username": basic_info.get("public_identifier"),
            "github_username": None,
            "social_urls": {},
            "profile_pic": basic_info.get("profile_picture_url") or raw_data.get("profile_picture_url"),
            "emails": [],
            "phonenumbers": [],
            "followers": basic_info.get("follower_count") if isinstance(basic_info.get("follower_count"), int) else None,
            "gender": None,
            "tier": None,
            "seniority_level": None,
            "primary_domain": None,
            "normalized_skills": None,
            "source": "apify",
            "last_scored_at": None,
            "created_at": None,
            "updated_at": None,
            "enriched_at": None,
        }
        return profile, None
    except Exception as e:
        return {}, f"Parse error: {str(e)}"
