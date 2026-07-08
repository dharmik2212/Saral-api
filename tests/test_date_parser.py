import pytest
from datetime import date
from src.utils.date_parser import parse_date, calc_months, is_current_role, generate_duration_text, effective_end_date, format_month_year


class TestParseDate:
    def test_full_date(self):
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)
    
    def test_month_year(self):
        result = parse_date("Jan 2024")
        assert result is not None
        assert result.year == 2024
    
    def test_full_month_year(self):
        result = parse_date("January 2024")
        assert result is not None
        assert result.year == 2024
    
    def test_none_input(self):
        result = parse_date(None)
        assert result is None
    
    def test_empty_string(self):
        result = parse_date("")
        assert result is None
    
    def test_present_marker_removed(self):
        result = parse_date("Jan 2024 - Present")
        assert result is not None
        assert result.year == 2024


class TestCalcMonths:
    def test_same_year(self):
        result = calc_months(date(2024, 1, 1), date(2024, 6, 1))
        assert result == 5
    
    def test_different_years(self):
        result = calc_months(date(2022, 3, 1), date(2024, 5, 1))
        assert result == 26
    
    def test_none_end_uses_today(self):
        result = calc_months(date(2024, 1, 1), None)
        assert result >= 0
    
    def test_same_month(self):
        result = calc_months(date(2024, 1, 1), date(2025, 1, 1))
        assert result == 12


class TestIsCurrentRole:
    def test_present(self):
        assert is_current_role("Jan 2024 - Present") is True
    
    def test_current(self):
        assert is_current_role("Jan 2024 - Current") is True
    
    def test_now(self):
        assert is_current_role("Jan 2024 - Now") is True
    
    def test_specific_date(self):
        assert is_current_role("Jan 2024 - Dec 2025") is False
    
    def test_none(self):
        assert is_current_role(None) is True
    
    def test_empty(self):
        assert is_current_role("") is True


class TestFormatMonthYear:
    def test_january(self):
        assert format_month_year(date(2024, 1, 15)) == "Jan 2024"

    def test_december(self):
        assert format_month_year(date(2024, 12, 1)) == "Dec 2024"


class TestGenerateDurationText:
    def test_past_role(self):
        text = generate_duration_text(date(2022, 1, 1), date(2023, 12, 1), False, 23)
        assert "Jan 2022" in text
        assert "Dec 2023" in text

    def test_current_role(self):
        text = generate_duration_text(date(2024, 6, 1), None, True, 12)
        assert "Present" in text

    def test_none_start(self):
        text = generate_duration_text(None, date(2024, 1, 1), False, 12)
        assert text is None

    def test_none_months(self):
        text = generate_duration_text(date(2024, 1, 1), date(2024, 6, 1), False, None)
        assert text is None

    def test_zero_months(self):
        text = generate_duration_text(date(2024, 1, 1), date(2024, 1, 1), False, 0)
        assert "0 mos" in text


class TestEffectiveEndDate:
    def test_current_role(self):
        result = effective_end_date(None, True)
        assert result == date.today().isoformat()

    def test_past_role(self):
        result = effective_end_date(date(2024, 12, 1), False)
        assert result == "2024-12-01"

    def test_no_end_not_current(self):
        result = effective_end_date(None, False)
        assert result is None