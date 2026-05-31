import copy
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from .config_presets import DEFAULT_CONFIG, get_domain_preset
from .enums.domain import Domain
from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.portrait_strategy import PortraitStrategy
from .schemas.config_schema import AppConfig
from .utils.json_utils import load_json

logger = logging.getLogger(__name__)

__all__ = ["load_config", "apply_cli_overrides"]


RECURSIVE_CONFIG_SECTIONS = {"site_labels", "site_rendering"}


def _validate_config(config: dict[str, Any]) -> AppConfig:
    try:
        return AppConfig(**config)
    except ValidationError as e:
        error_lines = [f"[AppConfig] {' > '.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
        formatted = "\n".join(error_lines)
        raise ValueError(f"Validation failed for config:\n{formatted}")


def _merge_nested_section(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _merge_nested_section(current, value)
        else:
            target[key] = value


def _merge_config_section(config: dict[str, Any], section_name: str, section_config: dict[str, Any]) -> None:
    if section_name in RECURSIVE_CONFIG_SECTIONS:
        _merge_nested_section(config[section_name], section_config)
        return

    config[section_name].update(section_config)


def _apply_domain_preset(config: dict[str, Any], domain: Domain) -> None:
    config["site_rendering"]["project_metadata"]["fields"] = {}
    for section_name, section_overrides in get_domain_preset(domain).sections().items():
        _merge_config_section(config, section_name, section_overrides)


def _merge_user_config(config: dict[str, Any], user_config: dict[str, Any], user_config_path: Path) -> None:
    if not isinstance(user_config, dict):
        raise ValueError(f"Config file must contain a JSON object: {user_config_path}")

    allowed_sections = set(config)
    extra_sections = sorted(set(user_config) - allowed_sections)
    if extra_sections:
        raise ValueError(f"Unknown config section(s): {', '.join(extra_sections)}")

    for section_name, section_config in user_config.items():
        if not isinstance(section_config, dict):
            raise ValueError(f"Config section '{section_name}' must contain a JSON object")
        _merge_config_section(config, section_name, section_config)


def load_config(user_config_path: Path = None) -> AppConfig:
    config = copy.deepcopy(DEFAULT_CONFIG)

    if user_config_path:
        user_config = load_json(user_config_path)
        _merge_user_config(config, user_config, user_config_path)
        logger.info(f"Loaded configuration from {user_config_path}")

    return _validate_config(config)


def apply_cli_overrides(
    config: AppConfig,
    image_sample_strategy: Optional[ImageSampleStrategy] = None,
    portrait_strategy: Optional[PortraitStrategy] = PortraitStrategy.NAMED,
    domain: Optional[Domain] = None,
) -> AppConfig:
    config_data = config.model_dump(mode="python")

    if domain is not None:
        _apply_domain_preset(config_data, domain)

    if image_sample_strategy is not None:
        config_data["media_rules"]["image_gallery_sample_strategy"] = image_sample_strategy

    match portrait_strategy:
        case PortraitStrategy.NONE:
            config_data["media_rules"]["auto_find_portraits"] = False
            config_data["site_rendering"]["portraits"]["hide"] = True
        case PortraitStrategy.NAMED:
            config_data["media_rules"]["auto_find_portraits"] = False
            config_data["site_rendering"]["portraits"]["hide"] = False
        case PortraitStrategy.AUTO:
            config_data["media_rules"]["auto_find_portraits"] = True
            config_data["site_rendering"]["portraits"]["hide"] = False

    return _validate_config(config_data)
