import json
import copy
from enum import Enum
from pathlib import Path

# === Default internal config ===
DEFAULT_CONFIG = {
    "html_settings": {
        "creator_label": "Creator",
        "project_label": "Project"
    },
    "media_rules": {
        "GLOBAL_EXCLUDE_RE": r"(^|/|\\)_",
        "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
        "VIDEO_EXCLUDE_RE": r"$^",
        "IMAGE_INCLUDE_RE": r"^[^/\\]+/[^/\\]+\.jpg$",
        "IMAGE_EXCLUDE_RE": r"$^"
    }
}

# === Build modes ===
class BuildMode(str, Enum):
    FLAT = "flat"
    HYBRID = "hybrid"
    DEEP = "deep"

def get_media_rules(mode: BuildMode) -> dict:
    match mode:
        case BuildMode.FLAT:
            return {
                "GLOBAL_EXCLUDE_RE": r"(^|/|\\)_",
                "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r"^[^/\\]+\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^"
            }
        case BuildMode.HYBRID:
            return copy.deepcopy(DEFAULT_CONFIG["media_rules"])
        case BuildMode.DEEP:
            return {
                "GLOBAL_EXCLUDE_RE": r"(^|/|\\)_",
                "VIDEO_INCLUDE_RE": r".*\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r".*\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^"
            }
        case _:
            raise ValueError(f"Unknown build mode: {mode}")


def load_config(config_path: Path = None) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            config["html_settings"].update(user_config.get("html_settings", {}))
            config["media_rules"].update(user_config.get("media_rules", {}))
            print(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
            print("Proceeding with default internal configuration.")

    return config

