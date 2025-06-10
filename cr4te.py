import sys
import argparse
import webbrowser
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config as cfg
from html_builder import clear_output_folder, build_html_pages
from json_builder import build_creator_json_files, clean_creator_json_files

__version__ = "0.0.1"

def _load_config(config_path_arg: str) -> Dict[str, Any]:
    config_path = Path(config_path_arg).resolve() if config_path_arg else None
    return cfg.load_config(config_path)

def main():
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    
    parser.add_argument("-v","--version", action="version", version=f"cr4te v{__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build-json
    json_parser = subparsers.add_parser("build-json", help="Generate JSON metadata from media folders")
    json_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    json_parser.add_argument("--config", help="Path to configuration file (optional)")
    json_parser.add_argument("--max-images", type=int, default=20, help="Maximum number of images to include per media group")
    json_parser.add_argument("--image-sample-strategy", choices=[s.value for s in cfg.ImageSampleStrategy], default=cfg.ImageSampleStrategy.SPREAD.value, help="Strategy to sample images: spread (default), head, all")
    
    # clean-json
    clean_parser = subparsers.add_parser("clean-json", help="Delete cr4te.json files from all creator folders")
    clean_parser.add_argument("-i", "--input", required=True, help="Path to input folder containing creators")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without removing anything")
    clean_parser.add_argument("--force", action="store_true", help="Actually delete files instead of showing a preview")

    # build-html
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser.add_argument("-o", "--output", required=True, help="Path to the HTML output folder")
    html_parser.add_argument("--config", help="Path to configuration file (optional)")
    html_parser.add_argument("--html-preset", choices=[m.value for m in cfg.HtmlPreset], default=cfg.HtmlPreset.ARTIST, help="Apply a preset label scheme for HTML: artist (default), musician, director, author, model")
    html_parser.add_argument('--open', action='store_true', help="Open index.html in the default browser after building.")
    html_parser.add_argument("--force", action="store_true", help="Delete the output folder and its contents (except thumbnails) without confirmation")
    html_parser.add_argument("--clean", action="store_true", help="Also delete the thumbnails folder (only valid with --force)")
    
    args = parser.parse_args()
    
    if args.command == "build-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return
            
        config = _load_config(args.config)
     
        config = cfg.apply_cli_media_overrides(
            config,
            image_gallery_max=args.max_images,
            image_sample_strategy=cfg.ImageSampleStrategy(args.image_sample_strategy)
        )
        
        build_creator_json_files(input_path, config["media_rules"])
        
    elif args.command == "clean-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        if not args.force and not args.dry_run:
            confirm = input(f"Delete all cr4te.json files in '{input_path}'? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborting.")
                return

        clean_creator_json_files(input_path, dry_run=args.dry_run)

    elif args.command == "build-html":
        if not args.force and args.clean:
            parser.error("--clean must be used together with --force")
        
        input_path = Path(args.input).resolve()
        output_path = Path(args.output).resolve()

        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        if output_path.exists():
            confirm = 'y' if args.force else input(f"Output folder '{output_path}' already exists. Delete everything except thumbnails and rebuild? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborting.")
                return
            clear_output_folder(output_path, args.clean)
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            
        config = _load_config(args.config)

        config = cfg.update_html_labels(config, args.html_preset)
        
        html_index_path = build_html_pages(input_path, output_path, config["html_settings"])
        
        if args.open:
            webbrowser.open(f"file://{html_index_path.resolve()}")

if __name__ == "__main__":
    main()

