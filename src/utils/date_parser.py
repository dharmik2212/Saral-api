from datetime import date, datetime
from dateutil import parser
from typing import Optional
import re


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse various date formats to Python date object.
    
    Handles:
    - "Jan 2024"
    - "January 2024"
    - "01/2024"
    - "2024-01-01"
    - "Jan 2024 - Present"
    
    Returns None if parsing fails or date is invalid.
    """
    if not date_str or date_str.strip() == "":
        return None
    
    # Clean the string
    date_str = date_str.strip()
    
    # Remove "Present" or similar markers
    date_str = re.sub(r'\s*[-–]\s*(Present|Current|Now)', '', date_str, flags=re.IGNORECASE)
    date_str = date_str.strip()
    
    if not date_str:
        return None
    
    try:
        # Try parsing with dateutil (flexible)
        parsed = parser.parse(date_str, default=datetime(2000, 1, 1))
        
        # If day is missing (default was used), default to 1st
        # dateutil might give day=1 when not specified
        return parsed.date()
    except (ValueError, parser.ParserError):
        return None


def calc_months(start: date, end: Optional[date] = None) -> int:
    """
    Calculate duration in months between two dates.
    
    Rule: (end_year - start_year) * 12 + (end_month - start_month)
    
    If end is None (ongoing role), use today's date.
    """
    if end is None:
        end = date.today()
    
    return (end.year - start.year) * 12 + (end.month - start.month)


def is_current_role(end_date_str: Optional[str]) -> bool:
    """Check if the role is marked as current."""
    if not end_date_str:
        return True
    
    end_lower = end_date_str.lower().strip()
    current_indicators = ['present', 'current', 'now', 'till date']
    
    return any(indicator in end_lower for indicator in current_indicators)


def format_month_year(d: date) -> str:
    """Format date as 'Mon YYYY' e.g. 'Jun 2025'"""
    return d.strftime("%b %Y")


def generate_duration_text(start: Optional[date], end: Optional[date], is_current: bool, duration_months: Optional[int]) -> Optional[str]:
    """
    Generate human-readable duration text matching engine format.
    Example: "Jun 2025 - Present · 1 yrs 2 mos" or "Jun 2022 - Dec 2024 · 2 yrs 6 mos"
    Returns None if start_date is missing.
    """
    if not start or duration_months is None:
        return None
    
    start_str = format_month_year(start)
    if is_current or end is None:
        end_str = "Present"
    else:
        end_str = format_month_year(end)
    
    years = duration_months // 12
    months = duration_months % 12
    parts = []
    if years > 0:
        parts.append(f"{years} yr{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} mo{'s' if months != 1 else ''}")
    if not parts:
        parts.append("0 mos")
    duration_part = " ".join(parts)
    
    return f"{start_str} - {end_str} · {duration_part}"


def effective_end_date(end_date: Optional[date], is_current: bool) -> Optional[str]:
    """Compute effective_end: actual end_date isoformat, or today if current, or None."""
    if is_current:
        return date.today().isoformat()
    if end_date:
        return end_date.isoformat()
    return None