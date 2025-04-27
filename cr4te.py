import argparse
import shutil
import copy
from pathlib import Path
from enum import Enum

import json

from html_builder import clear_output_folder, collect_creator_data, build_html_pages
from json_builder import process_all_creators

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

def get_media_rules_for_mode(mode: BuildMode) -> dict:
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

def main():
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build-json
    json_parser = subparsers.add_parser("build-json", help="Generate JSON metadata from media folders")
    json_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    json_parser.add_argument("--config", help="Path to configuration file (optional)")
    json_parser.add_argument("--mode", choices=[m.value for m in BuildMode], default=BuildMode.HYBRID.value, help="Media discovery mode: flat, hybrid (default), deep")

    # build-html
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser.add_argument("-o", "--output", required=True, help="Path to the HTML output folder")
    html_parser.add_argument("--config", help="Path to configuration file (optional)")

    args = parser.parse_args()

    if args.command == "build-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        if args.config:
            config = load_config(Path(args.config).resolve())
        else:
            config = {
                "html_settings": DEFAULT_CONFIG["html_settings"],
                "media_rules": get_media_rules_for_mode(BuildMode(args.mode))
            }

        process_all_creators(input_path, config["media_rules"])

    elif args.command == "build-html":
        input_path = Path(args.input).resolve()
        output_path = Path(args.output).resolve()

        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        if output_path.exists():
            confirm = input(f"Output folder '{output_path}' already exists. Delete everything except thumbnails and rebuild? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborting.")
                return
            clear_output_folder(output_path)
        else:
            output_path.mkdir(parents=True, exist_ok=True)

        if args.config:
            config = load_config(Path(args.config).resolve())
        else:
            config = load_config()

        creator_data = collect_creator_data(input_path)

        build_html_pages(creator_data, input_path, output_path, config["html_settings"])

if __name__ == "__main__":
    main()

