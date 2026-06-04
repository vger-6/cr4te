from __future__ import annotations

from datetime import datetime

__all__ = ["dated_title_sort_key"]


def dated_title_sort_key(date_value: datetime | None, title: str) -> tuple:
    return (date_value or datetime.max, title.lower())
