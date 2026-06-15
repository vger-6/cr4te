from string import Formatter

__all__ = ["format_named", "validate_named_format"]


def format_named(format_string: str, **values: str) -> str:
    return format_string.format(**values)


def validate_named_format(
    value: str,
    *,
    allowed_fields: frozenset[str],
    required_fields: frozenset[str],
) -> str:
    try:
        parsed = list(Formatter().parse(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("must be a valid format string") from exc

    fields: list[str] = []
    for _, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name not in allowed_fields or format_spec or conversion:
            placeholders = ", ".join(f"{{{field}}}" for field in sorted(allowed_fields))
            raise ValueError(f"must use only the named placeholders {placeholders}")
        fields.append(field_name)

    duplicate_fields = sorted(field for field in allowed_fields if fields.count(field) > 1)
    if duplicate_fields:
        placeholders = ", ".join(f"{{{field}}}" for field in duplicate_fields)
        raise ValueError(f"must not repeat placeholders: {placeholders}")

    missing_fields = sorted(required_fields - set(fields))
    if missing_fields:
        placeholders = ", ".join(f"{{{field}}}" for field in missing_fields)
        raise ValueError(f"must contain required placeholders: {placeholders}")

    return value
