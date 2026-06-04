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
    "MetadataReferenceError",
    "MetadataShapeError",
    "MetadataValidationError",
    "load_json_model",
    "metadata_path",
    "metadata_relative_path",
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


class MetadataReferenceError(MetadataLoadError):
    issue_code = IssueCode.MISSING_REFERENCE


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


def metadata_relative_path(folder: Path, configured_path: str, input_dir: Path, field_name: str) -> str:
    if not configured_path:
        return ""

    raw_path = Path(configured_path)
    full_path = raw_path if raw_path.is_absolute() else folder / raw_path
    resolved_path = full_path.resolve()
    resolved_input_dir = input_dir.resolve()

    if not resolved_path.is_relative_to(resolved_input_dir):
        raise MetadataReferenceError(f"{field_name} must point inside the input directory: {configured_path}")
    if not resolved_path.is_file():
        raise MetadataReferenceError(f"{field_name} file not found: {full_path}")

    return resolved_path.relative_to(resolved_input_dir).as_posix()

