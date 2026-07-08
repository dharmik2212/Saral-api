from fastapi import FastAPI, HTTPException
from uuid import UUID

from src.models import get_candidates_collection
from src.models.schemas import ProfileResponse
from src.utils.duration import compute_total_experience_months

app = FastAPI(title="Saral API", version="1.0.0")


def doc_to_response(doc: dict) -> dict:
    experiences_data = doc.get("experiences") or []
    total_months = compute_total_experience_months(experiences_data)

    return {
        "status": "success",
        "profile": {
            "id": doc["id"],
            "name": doc.get("name") or doc.get("full_name"),
            "headline": doc.get("headline"),
            "about": doc.get("about"),
            "location": doc.get("location"),
            "location_city": doc.get("location_city"),
            "location_state": doc.get("location_state"),
            "location_country": doc.get("location_country"),
            "current_company": doc.get("current_company"),
            "current_role": doc.get("current_role"),
            "work_mode": doc.get("work_mode"),
            "total_experience_months": total_months,
            "skills": doc.get("skills") or [],
            "experience": experiences_data,
            "education": doc.get("education") or [],
            "featured": doc.get("featured"),
            "is_open_to_work": doc.get("is_open_to_work", False),
            "linkedin_url": doc.get("linkedin_url") or doc["linkedin_url"],
            "github_url": doc.get("github_url"),
            "linkedin_username": doc.get("linkedin_username"),
            "github_username": doc.get("github_username"),
            "social_urls": doc.get("social_urls") or {},
            "profile_pic": doc.get("profile_pic"),
            "emails": doc.get("emails") or [],
            "phonenumbers": doc.get("phonenumbers") or [],
            "followers": doc.get("followers"),
            "gender": doc.get("gender"),
            "tier": doc.get("tier"),
            "seniority_level": doc.get("seniority_level"),
            "primary_domain": doc.get("primary_domain"),
            "normalized_skills": doc.get("normalized_skills"),
            "source": doc.get("source"),
            "last_scored_at": doc.get("last_scored_at"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "enriched_at": doc.get("enriched_at"),
        },
    }


@app.get("/api/saral/profile/{candidate_id}", response_model=ProfileResponse)
async def get_profile(candidate_id: UUID):
    col = get_candidates_collection()
    doc = await col.find_one({"id": str(candidate_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return doc_to_response(doc)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
