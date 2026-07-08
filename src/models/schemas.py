from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class Company(BaseModel):
    company_name: str
    company_id: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_image_url: Optional[str] = None
    s3_company_logo: Optional[str] = None
    max_end: Optional[str] = None
    min_start: Optional[str] = None
    span_text: Optional[str] = None
    span_months: Optional[int] = None


class Position(BaseModel):
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    duration_text: Optional[str] = None
    duration_months: Optional[int] = None
    effective_end: Optional[str] = None
    job_type: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    description: Optional[str] = None
    skills_used: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: Company
    positions: list[Position] = Field(default_factory=list)


class Education(BaseModel):
    degree: Optional[str] = None
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    school_name: Optional[str] = None
    school_id: Optional[str] = None
    school_linkedin_url: Optional[str] = None
    school_logo: Optional[str] = None
    s3_school_logo: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period: Optional[str] = None
    description: Optional[str] = None


class Featured(BaseModel):
    link: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    slides: list[dict] = Field(default_factory=list)
    subtitle: Optional[str] = None


class ProfileData(BaseModel):
    id: str
    name: str
    headline: Optional[str] = None
    about: Optional[str] = None
    location: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    work_mode: Optional[str] = None
    total_experience_months: int = 0
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    featured: Optional[Featured] = None
    is_open_to_work: bool = False
    linkedin_url: str
    github_url: Optional[str] = None
    linkedin_username: Optional[str] = None
    github_username: Optional[str] = None
    social_urls: dict = Field(default_factory=dict)
    profile_pic: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    phonenumbers: list[str] = Field(default_factory=list)
    followers: Optional[int] = None
    gender: Optional[str] = None
    tier: Optional[str] = None
    seniority_level: Optional[str] = None
    primary_domain: Optional[str] = None
    normalized_skills: Optional[list[str]] = None
    source: Optional[str] = None
    last_scored_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    enriched_at: Optional[str] = None


class ProfileResponse(BaseModel):
    status: str = "success"
    profile: ProfileData
