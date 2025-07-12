from datetime import datetime
from typing import Optional

# TODO: use logging instead of print()

__all__ = ["parse_date", "calculate_age", "calculate_age_from_strings"]

def parse_date(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError) as e:
        print(f"Failed to parse date '{date_str}': {e}")
        return None

def calculate_age(dob: datetime, date: datetime) -> Optional[int]:
    try:
        age = date.year - dob.year - ((date.month, date.day) < (dob.month, dob.day))
        return age
    except Exception as e:
        print(f"Error calculating age: {e}")
        return None
   
def calculate_age_from_strings(date_of_birth_str: str, reference_date_str: str) -> Optional[int]:
    """
    Safely parses two date strings and returns age as int.
    Returns None if either date is missing or invalid.
    """
    dob = parse_date(date_of_birth_str)
    ref = parse_date(reference_date_str)
    if dob and ref:
        return calculate_age(dob, ref)
    return None
