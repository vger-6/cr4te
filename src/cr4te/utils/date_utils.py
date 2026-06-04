import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = [
    "calculate_age_from_strings",
    "format_age",
    "format_nice_date",
    "normalize_optional_iso_date",
    "parse_date",
]


DATE_FORMATS = (
    (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
    (r"\d{4}-\d{2}", "%Y-%m"),
    (r"\d{4}", "%Y"),
)


def _date_format_for(normalized: str) -> str | None:
    for pattern, fmt in DATE_FORMATS:
        if re.fullmatch(pattern, normalized):
            return fmt
    return None


def normalize_optional_iso_date(date_str: Optional[str]) -> str:
    if date_str is None:
        return ""

    if not isinstance(date_str, str):
        raise ValueError(f"Expected string or None, got {type(date_str)}")

    normalized = date_str.strip()
    if not normalized:
        return ""

    fmt = _date_format_for(normalized)
    if fmt:
        try:
            datetime.strptime(normalized, fmt)
        except ValueError as exc:
            raise ValueError(f"Invalid date format: '{normalized}'") from exc
        return normalized

    raise ValueError(f"{normalized} must be in yyyy, yyyy-mm, yyyy-mm-dd format or empty")


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string in YYYY, YYYY-MM, or YYYY-MM-DD format."""
    try:
        normalized = normalize_optional_iso_date(date_str)
    except ValueError:
        logger.warning(f"Failed to parse date '{date_str}'")
        return None

    if not normalized:
        return None

    fmt = _date_format_for(normalized)
    return datetime.strptime(normalized, fmt) if fmt else None


def format_nice_date(date_str: Optional[str]) -> str:
    """
    Convert a normalized date string into a human-friendly format:
      - 1926-05-26 -> May 26, 1926
      - 1926-05    -> May 1926
      - 1926       -> 1926
    Returns empty string if input is empty or invalid.
    """
    if not date_str:
        return ""

    dt = parse_date(date_str)
    if not dt:
        return str(date_str).strip()  # fallback

    original = str(date_str).strip()

    if len(original) == 4:
        return original
    if len(original) == 7:
        return dt.strftime("%B %Y")
    if len(original) == 10:
        return dt.strftime("%B %d, %Y")
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
        10  -> "10 y.o."
         0  -> "0 y.o."
        None -> ""
    """
    if age is None or age < 0:
        return ""
    return f"{age} y.o."
