from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import ValidationError

from .build_issues import IssueCode
from .constants import CR4TE_JSON_FILE_NAME
from .utils.date_utils import normalize_optional_iso_date

__all__ = [
    "MetadataIOError",
    "MetadataJsonError",
    "MetadataLoadError",
    "MetadataShapeError",
    "MetadataValidationError",
    "load_json_model",
    "metadata_path",
    "normalize_metadata_date",
]

ModelT = TypeVar("ModelT")


class MetadataLoadError(ValueError):
    issue_code = IssueCode.INVALID_METADATA


class MetadataJsonError(MetadataLoadError):
    issue_code = IssueCode.INVALID_JSON


class MetadataShapeError(MetadataLoadError):
    issue_code = IssueCode.INVALID_METADATA_SHAPE


class MetadataValidationError(MetadataLoadError):
    issue_code = IssueCode.INVALID_METADATA


class MetadataIOError(MetadataLoadError):
    issue_code = IssueCode.IO_ERROR


def normalize_metadata_date(date_str: Optional[str], field_name: str, context_name: str) -> str:
    try:
        return normalize_optional_iso_date(date_str)
    except ValueError as exc:
        raise MetadataValidationError(f"{context_name}: invalid {field_name}: {date_str} ({exc})") from exc


def load_json_model(path: Path, model_type: type[ModelT]) -> ModelT:
    if not path.exists():
        return model_type()

    try:
        with open(path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
        if not isinstance(raw_data, dict):
            raise MetadataShapeError(f"Metadata file must contain a JSON object: {path}")
        return model_type(**raw_data)
    except JSONDecodeError as exc:
        raise MetadataJsonError(f"Invalid JSON in metadata file {path}: {exc.msg}") from exc
    except ValidationError as exc:
        errors = [f"{' > '.join(map(str, err['loc']))}: {err['msg']}" for err in exc.errors()]
        raise MetadataValidationError(f"Invalid metadata file {path}:\n" + "\n".join(errors)) from exc
    except OSError as exc:
        raise MetadataIOError(f"Unable to read metadata file {path}: {exc}") from exc


def metadata_path(folder: Path) -> Path:
    return folder / CR4TE_JSON_FILE_NAME
