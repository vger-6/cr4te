import argparse
import shutil
import json
from pathlib import Path

import config as cfg
from html_builder import clear_output_folder, build_html_pages
from json_builder import process_all_creators

__version__ = "0.0.1"

def main():
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    
    parser.add_argument("-v","--version", action="version", version=f"cr4te v{__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build-json
    json_parser = subparsers.add_parser("build-json", help="Generate JSON metadata from media folders")
    json_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    json_parser.add_argument("--config", help="Path to configuration file (optional)")
    json_parser.add_argument("--mode", choices=[m.value for m in cfg.BuildMode], default=cfg.BuildMode.HYBRID.value, help="Media discovery mode: flat, hybrid (default), deep")
    json_parser.add_argument("--max-images", type=int, default=20, help="Maximum number of images to include per media group")
    json_parser.add_argument("--image-sample-strategy", choices=[s.value for s in cfg.ImageSampleStrategy], default=cfg.ImageSampleStrategy.SPREAD.value, help="Strategy to sample images: spread (default), head, all")

    # build-html
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser.add_argument("-o", "--output", required=True, help="Path to the HTML output folder")
    html_parser.add_argument("--config", help="Path to configuration file (optional)")
    html_parser.add_argument("--html-preset", choices=[m.value for m in cfg.HtmlPreset], default=cfg.HtmlPreset.ARTIST, help="Apply a preset label scheme for HTML (artist [default], director, model)")
    
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
        
        config = cfg.apply_cli_media_overrides(
            config,
            max_images=args.max_images,
            image_strategy=args.image_sample_strategy
        )
        
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

        config = cfg.update_html_labels(config, args.html_preset)
        
        build_html_pages(input_path, output_path, config["html_settings"])

if __name__ == "__main__":
    main()

