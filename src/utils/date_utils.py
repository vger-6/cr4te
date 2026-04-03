import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = ["parse_date", "calculate_age_from_strings"]

def parse_date(date_str: str) -> Optional[datetime]:
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

def _calculate_age(dob: datetime, date: datetime) -> Optional[int]:
    try:
        age = date.year - dob.year - ((date.month, date.day) < (dob.month, dob.day))
        return age
    except Exception as e:
        logger.warning(f"Failed to calculate age: {e}")
        return None
   
def calculate_age_from_strings(date_of_birth_str: str, reference_date_str: str) -> Optional[int]:
    """
    Safely parses two date strings and returns age as int.
    Returns None if either date is missing or invalid.
    """
    dob = parse_date(date_of_birth_str)
    ref = parse_date(reference_date_str)
    if dob and ref:
        return _calculate_age(dob, ref)
    return None
