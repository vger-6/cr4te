import argparse
import json
import shutil
import copy
from pathlib import Path
from html_builder import clear_output_folder, collect_creator_data, build_html_pages
from json_builder import process_all_creators

# Default internal config
DEFAULT_CONFIG = {
    "html_settings": {
        "creator_label": "Creator",
        "project_label": "Project"
    },
    "media_rules": {
        "GLOBAL_EXCLUDE_RE": r"(^|/|\\)_",
        "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",  # root-level only
        "VIDEO_EXCLUDE_RE": r"$^",  # match nothing (placeholder)
        "IMAGE_INCLUDE_RE": r"^[^/\\]+/[^/\\]+\.jpg$",  # immediate subfolders only
        "IMAGE_EXCLUDE_RE": r"$^"  # match nothing (placeholder)
    }
}

def load_config(config_path: Path = None) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    # If no path explicitly given, check if config/cr4te_config.json exists
    if config_path is None:
        default_config_path = Path(__file__).parent / "config" / "cr4te_config.json"
        if default_config_path.exists():
            config_path = default_config_path

    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            # Deep merge
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

    # build-html
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser.add_argument("-o", "--output", required=True, help="Path to output HTML site folder")
    html_parser.add_argument("--config", help="Path to configuration file (optional)")

    args = parser.parse_args()

    config = load_config(Path(args.config).resolve()) if args.config else DEFAULT_CONFIG

    if args.command == "build-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return
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

        creator_data = collect_creator_data(input_path)
        build_html_pages(creator_data, output_path, input_path, config["html_settings"])

if __name__ == "__main__":
    main()

