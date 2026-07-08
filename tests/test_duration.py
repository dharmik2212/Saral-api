import pytest
from datetime import date
from src.utils.duration import parse_position, parse_experiences, build_experiences, compute_total_experience_months
from src.utils.date_parser import generate_duration_text, effective_end_date


class TestParsePosition:
    def test_valid_position(self):
        pos = {
            "title": "Engineer",
            "company": "Tech Corp",
            "startDate": "Jan 2022",
            "endDate": "Dec 2023",
        }
        result = parse_position(pos)
        assert result is not None
        assert result["role"] == "Engineer"
        assert result["company_name"] == "Tech Corp"
        assert result["is_current"] is False
        assert result["duration_months"] == 23
        assert result["end_date"] is not None

    def test_current_role(self):
        pos = {
            "title": "Engineer",
            "company": "Tech Corp",
            "startDate": "Jan 2022",
            "endDate": "Present",
        }
        result = parse_position(pos)
        assert result is not None
        assert result["is_current"] is True
        assert result["end_date"] is None
        assert result["duration_months"] is not None
        assert "Present" in result.get("duration_text", "")

    def test_empty_role_and_company_skipped(self):
        pos = {"title": "", "companyName": ""}
        result = parse_position(pos)
        assert result is None

    def test_empty_role_with_company_allowed(self):
        pos = {"title": "", "company": "Tech Corp"}
        result = parse_position(pos)
        assert result is not None
        assert result["company_name"] == "Tech Corp"

    def test_empty_company_with_role_allowed(self):
        pos = {"title": "Engineer", "company": ""}
        result = parse_position(pos)
        assert result is not None
        assert result["role"] == "Engineer"

    def test_missing_start_date(self):
        pos = {"title": "Engineer", "company": "Tech Corp", "endDate": "Dec 2023"}
        result = parse_position(pos)
        assert result is not None
        assert result["start_date"] is None
        assert result["duration_months"] is None
        assert result["duration_text"] is None


class TestParseExperiences:
    def test_empty_response(self):
        result = parse_experiences({})
        assert result == []

    def test_flat_experiences_list(self):
        raw = {
            "experiences": [
                {
                    "title": "Engineer",
                    "company": "Tech Corp",
                    "startDate": "Jan 2022",
                    "endDate": "Dec 2023",
                }
            ]
        }
        result = parse_experiences(raw)
        assert len(result) == 1
        company = result[0]["company"]
        positions = result[0]["positions"]
        assert company["company_name"] == "Tech Corp"
        assert len(positions) == 1
        assert positions[0]["role"] == "Engineer"
        assert positions[0]["duration_months"] == 23

    def test_pre_grouped_experiences(self):
        raw = {
            "experiences": [
                {
                    "company": {"companyName": "Tech Corp", "companyId": "12345"},
                    "positions": [
                        {
                            "title": "Engineer",
                            "startDate": "Jan 2022",
                            "endDate": "Dec 2023",
                        }
                    ]
                }
            ]
        }
        result = parse_experiences(raw)
        assert len(result) == 1
        assert result[0]["company"]["company_name"] == "Tech Corp"
        assert result[0]["company"]["company_id"] == "12345"
        assert len(result[0]["positions"]) == 1
        assert result[0]["positions"][0]["role"] == "Engineer"

    def test_mixed_valid_and_invalid_positions(self):
        raw = {
            "experiences": [
                {
                    "title": "Engineer",
                    "company": "Tech Corp",
                    "startDate": "Jan 2022",
                    "endDate": "Dec 2023",
                },
                {
                    "title": "",
                    "company": "",
                },
            ]
        }
        result = parse_experiences(raw)
        assert len(result) == 1
        assert len(result[0]["positions"]) == 1  # Skipped the bad one

    def test_current_role_in_flat_list(self):
        raw = {
            "experience": [
                {
                    "title": "Head of Operations",
                    "company": "RoadVision AI",
                    "startDate": "Jan 2026",
                    "endDate": "Present",
                }
            ]
        }
        result = parse_experiences(raw)
        assert len(result) == 1
        pos = result[0]["positions"][0]
        assert pos["is_current"] is True
        assert pos["end_date"] is None
        assert pos["duration_months"] is not None


class TestBuildExperiences:
    def test_single_company_single_position(self):
        positions_meta = [{
            "role": "Engineer",
            "company_name": "Tech Corp",
            "start_date": "2022-01-01",
            "end_date": "2023-12-01",
            "is_current": False,
            "duration_text": "Jan 2022 - Dec 2023 · 1 yr 11 mos",
            "duration_months": 23,
            "effective_end": "2023-12-01",
            "job_type": None,
            "location": None,
            "work_type": None,
            "description": None,
            "skills_used": [],
            "company_id": None,
            "company_linkedin_url": None,
            "company_image_url": None,
        }]
        result = build_experiences(positions_meta)
        assert len(result) == 1
        assert result[0]["company"]["company_name"] == "Tech Corp"
        assert result[0]["company"]["min_start"] == "2022-01-01"
        assert result[0]["company"]["max_end"] == "2023-12-01"
        assert result[0]["company"]["span_months"] == 23
        assert len(result[0]["positions"]) == 1

    def test_multiple_positions_same_company_grouped(self):
        positions_meta = [
            {
                "role": "Engineer",
                "company_name": "Tech Corp",
                "start_date": "2022-01-01",
                "end_date": "2023-12-01",
                "is_current": False,
                "duration_months": 23,
            },
            {
                "role": "Senior Engineer",
                "company_name": "Tech Corp",
                "start_date": "2024-01-01",
                "end_date": "2025-06-01",
                "is_current": False,
                "duration_months": 17,
            },
        ]
        result = build_experiences(positions_meta)
        assert len(result) == 1
        assert result[0]["company"]["company_name"] == "Tech Corp"
        assert len(result[0]["positions"]) == 2
        assert result[0]["company"]["span_months"] == 41  # Jan 2022 to Jun 2025

    def test_different_companies_separate_groups(self):
        positions_meta = [
            {"role": "Engineer", "company_name": "Tech Corp", "start_date": "2022-01-01", "end_date": "2023-12-01", "is_current": False, "duration_months": 23},
            {"role": "Manager", "company_name": "Startup Inc", "start_date": "2024-01-01", "end_date": None, "is_current": True, "duration_months": 30},
        ]
        result = build_experiences(positions_meta)
        assert len(result) == 2
        names = {e["company"]["company_name"] for e in result}
        assert names == {"Tech Corp", "Startup Inc"}


class TestComputeTotalExperienceMonths:
    def test_single_position(self):
        experiences = [{"company": {"company_name": "A"}, "positions": [{"duration_months": 23}]}]
        assert compute_total_experience_months(experiences) == 23

    def test_multiple_positions(self):
        experiences = [
            {"company": {"company_name": "A"}, "positions": [{"duration_months": 23}, {"duration_months": 17}]},
            {"company": {"company_name": "B"}, "positions": [{"duration_months": 6}]},
        ]
        assert compute_total_experience_months(experiences) == 46

    def test_null_months_ignored(self):
        experiences = [{"company": {"company_name": "A"}, "positions": [{"duration_months": 23}, {"duration_months": None}]}]
        assert compute_total_experience_months(experiences) == 23

    def test_empty_experiences(self):
        assert compute_total_experience_months([]) == 0


class TestDurationTextGeneration:
    def test_past_role_text(self):
        from src.utils.date_parser import generate_duration_text as gdt
        text = gdt(date(2022, 1, 1), date(2023, 12, 1), False, 23)
        assert "Jan 2022" in text
        assert "Dec 2023" in text
        assert "1 yr" in text
        assert "11 mos" in text

    def test_current_role_text(self):
        from src.utils.date_parser import generate_duration_text as gdt
        text = gdt(date(2024, 6, 1), None, True, 12)
        assert "Present" in text
        assert "1 yr" in text

    def test_less_than_one_year(self):
        from src.utils.date_parser import generate_duration_text as gdt
        text = gdt(date(2024, 1, 1), date(2024, 3, 1), False, 2)
        assert "2 mos" in text
