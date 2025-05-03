import argparse
import shutil
import json
from pathlib import Path

import config as cfg
from html_builder import clear_output_folder, collect_creator_data, build_html_pages
from json_builder import process_all_creators

def main():
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build-json
    json_parser = subparsers.add_parser("build-json", help="Generate JSON metadata from media folders")
    json_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    json_parser.add_argument("--config", help="Path to configuration file (optional)")
    json_parser.add_argument("--mode", choices=[m.value for m in cfg.BuildMode], default=cfg.BuildMode.HYBRID.value, help="Media discovery mode: flat, hybrid (default), deep")

    # build-html
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser.add_argument("-o", "--output", required=True, help="Path to the HTML output folder")
    html_parser.add_argument("--config", help="Path to configuration file (optional)")
    
    args = parser.parse_args()
    
    # load config
    config_path = Path(args.config).resolve() if args.config else None
    config = cfg.load_config(config_path)

    if args.command == "build-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        config = cfg.update_build_rules(config, args.mode)
        compiled_media_rules = cfg.compile_media_rules(config["media_rules"])
        process_all_creators(input_path, compiled_media_rules)

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

        build_html_pages(creator_data, input_path, output_path, config["html_settings"])

if __name__ == "__main__":
    main()

