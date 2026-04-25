import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = ["parse_date", "format_nice_date", "calculate_age_from_strings", "format_age"]


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string in YYYY, YYYY-MM, or YYYY-MM-DD format."""
    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()
    if not date_str:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Failed to parse date '{date_str}'")
    return None


def format_nice_date(date_str: Optional[str]) -> str:
    """
    Convert a normalized date string into a human-friendly format:
      - 1926-05-26 → May 26, 1926
      - 1926-05    → May 1926
      - 1926       → 1926
    Returns empty string if input is empty or invalid.
    """
    if not date_str:
        return ""

    dt = parse_date(date_str)
    if not dt:
        return str(date_str).strip()  # fallback

    # Decide formatting based on original precision
    original = str(date_str).strip()

    if len(original) == 4:          # Year only
        return original
    elif len(original) == 7:        # Year + Month
        return dt.strftime("%B %Y")
    elif len(original) == 10:       # Full date
        return dt.strftime("%B %d, %Y")
    else:
        # Fallback: use full date if we somehow got a datetime
        return dt.strftime("%B %d, %Y")


def _calculate_age(dob: datetime, reference: datetime) -> Optional[int]:
    """Calculate age at a given reference date."""
    try:
        age = reference.year - dob.year - ((reference.month, reference.day) < (dob.month, dob.day))
        return age
    except Exception as e:
        logger.warning(f"Failed to calculate age: {e}")
        return None


def calculate_age_from_strings(date_of_birth_str: Optional[str], reference_date_str: Optional[str]) -> Optional[int]:
    """
    Safely calculate age from two date strings.
    Returns None if either date is missing or invalid.
    """
    dob = parse_date(date_of_birth_str)
    ref = parse_date(reference_date_str)

    if dob and ref:
        return _calculate_age(dob, ref)
    return None
    
def format_age(age: Optional[int]) -> str:
    """
    Format age as a nice string for display.
    Examples:
        10  → "10 y.o."
         0  → "0 y.o."
        None → ""
    """
    if age is None or age < 0:
        return ""
    return f"{age} y.o."
