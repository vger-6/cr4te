import json
import copy
import re
from enum import Enum
from pathlib import Path
from typing import Dict

# === Default internal config ===
DEFAULT_CONFIG = {
    "html_settings": {
        "creator_label": "Creator",
        "project_label": "Project"
    },
    "media_rules": {
        "GLOBAL_EXCLUDE_RE": r"^_",
        "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
        "VIDEO_EXCLUDE_RE": r"$^",
        "IMAGE_INCLUDE_RE": r"^[^/\\]+/[^/\\]+\.jpg$",
        "IMAGE_EXCLUDE_RE": r"$^",
        "PORTRAIT_RE": r"^profile\.jpg$",
        "POSTER_RE": r"^cover\.jpg$",
        "MAX_IMAGES": 20,
        "IMAGE_SAMPLE_STRATEGY": "spread"
    }
}

class BuildMode(str, Enum):
    FLAT = "flat"
    HYBRID = "hybrid"
    DEEP = "deep"
    
class ImageSampleStrategy(Enum):
    SPREAD = "spread"
    HEAD = "head"

def get_build_rules(mode: BuildMode) -> Dict:
    """
    Returns only the regex-related media_rules fields that are overridden
    by the selected build mode. Other configuration fields remain untouched.
    """
    match mode:
        case BuildMode.FLAT:
            return {
                "GLOBAL_EXCLUDE_RE": r"^_",
                "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r"^[^/\\]+\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^"
            }
        case BuildMode.DEEP:
            return {
                "GLOBAL_EXCLUDE_RE": r"^_",
                "VIDEO_INCLUDE_RE": r".*\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r".*\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^"
            }
        case BuildMode.HYBRID:
            return {}  # Use the base/default media_rules
        case _:
            raise ValueError(f"Unknown build mode: {mode}")

def load_config(config_path: Path = None) -> Dict:
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

def update_build_rules(config: Dict, mode_str: str) -> Dict:
    """
    Given a mode string and an existing config dict, apply build-mode-specific
    regex overrides to the media_rules section and return the updated config.
    """
    mode = BuildMode(mode_str)
    overrides = get_build_rules(mode)
    config["media_rules"].update(overrides)
    return config
    
def compile_media_rules(media_rules: Dict) -> Dict:
    """
    Compiles all known regex patterns in media_rules into regular expressions.
    Other values (e.g., integers) are preserved as-is.
    """
    regex_keys = {
        "GLOBAL_EXCLUDE_RE", 
        "VIDEO_INCLUDE_RE", "VIDEO_EXCLUDE_RE", 
        "IMAGE_INCLUDE_RE", "IMAGE_EXCLUDE_RE", 
        "PORTRAIT_RE", "POSTER_RE"
    }
    enum_keys = {"IMAGE_SAMPLE_STRATEGY": ImageSampleStrategy}
    
    compiled = {}
    for key, val in media_rules.items():
        if key in regex_keys:
            compiled[key] = re.compile(val)
        elif key in enum_keys:
            compiled[key] = enum_keys[key](val)
        else:
            compiled[key] = val
    return compiled

