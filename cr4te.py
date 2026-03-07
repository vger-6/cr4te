import sys
import logging
import argparse
import webbrowser
import json
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config_manager as cfg
from enums.image_sample_strategy import ImageSampleStrategy
from enums.portrait_strategy import PortraitStrategy
from enums.domain import Domain
from html_builder import clear_output_folder, build_html_pages
from json_builder import build_creator_json_files, clean_creator_json_files

__version__ = "0.0.1"

YES_NO_STR = "[y/N]"

# Short flags
FLAG_INPUT_SHORT = "-i"
FLAG_OUTPUT_SHORT = "-o"

# Long Flags
FLAG_INPUT = "--input"
FLAG_OUTPUT = "--output"
FLAG_OPEN = "--open"
FLAG_FORCE = "--force"
FLAG_CLEAN = "--clean"

def _setup_logging():
    """Configures the global logging settings."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr
    )

def _validate_input_dir(path_str: str) -> Optional[Path]:
    input_dir = Path(path_str).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        logging.error(f"Input path does not exist or is not a directory: {input_dir}")
        return None
    return input_dir

def _load_config(rel_config_path_arg: str) -> Dict[str, Any]:
    config_path = Path(rel_config_path_arg).resolve() if rel_config_path_arg else None
    return cfg.load_config(config_path)

def main():
    _setup_logging()
    
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    
    parser.add_argument("-v","--version", action="version", version=f"cr4te v{__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_config_arguments(p: argparse.ArgumentParser):
        p.add_argument("--config", help="Path to configuration file (optional)")
        p.add_argument("--domain", choices=[m.value for m in Domain], help="Apply a domain-specific configuration preset")
        p.add_argument("--image-sample-strategy", choices=[s.value for s in ImageSampleStrategy], help="Strategy to sample images per folder")
        p.add_argument("--portrait-strategy", choices=[s.value for s in PortraitStrategy], help="Strategy to find portraits")

    # build
    build_parser = subparsers.add_parser("build", help="Generate JSON metadata and build HTML site")
    build_parser.add_argument(FLAG_INPUT_SHORT, FLAG_INPUT, required=True, help="Path to the Creators folder")
    build_parser.add_argument(FLAG_OUTPUT_SHORT, FLAG_OUTPUT, required=True, help="Path to the HTML output folder")
    _add_config_arguments(build_parser)
    build_parser.add_argument(FLAG_OPEN, action='store_true', help="Open index.html in the default browser after building.")
    build_parser.add_argument(FLAG_FORCE, action="store_true", help="Delete the output folder and its contents (except thumbnails) without confirmation")
    build_parser.add_argument(FLAG_CLEAN, action="store_true", help=f"Also delete the thumbnails folder (only valid with {FLAG_FORCE})")
    
    # print-config
    print_config_parser = subparsers.add_parser("print-config", help="Print the resolved configuration and exit")
    _add_config_arguments(print_config_parser)
    
    # clean-json
    clean_parser = subparsers.add_parser("clean-json", help="Delete cr4te.json files from all creator folders")
    clean_parser.add_argument(FLAG_INPUT_SHORT, FLAG_INPUT, required=True, help="Path to input folder containing creators")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without removing anything")
    clean_parser.add_argument(FLAG_FORCE, action="store_true", help="Actually delete files instead of showing a preview")
    
    args = parser.parse_args()
    
    if args.command == "build":
        config = _load_config(args.config)
        
        config = cfg.apply_cli_overrides(
            config,
            image_sample_strategy=ImageSampleStrategy(args.image_sample_strategy) if args.image_sample_strategy else None,
            portrait_strategy=PortraitStrategy(args.portrait_strategy) if args.portrait_strategy else None,
            domain=Domain(args.domain) if args.domain else None
        )

        if args.clean and not args.force:
            parser.error(f"{FLAG_CLEAN} must be used together with {FLAG_FORCE}")
        
        input_dir = _validate_input_dir(args.input)
        if input_dir is None:
            return
            
        output_dir = Path(args.output).resolve()
        if output_dir.exists():
            confirm = 'y' if args.force else input(f"Output folder '{output_dir}' already exists. Delete everything except thumbnails and rebuild? {YES_NO_STR}: ").strip().lower()
            if confirm != 'y':
                logging.info("Aborting.")
                return
            clear_output_folder(output_dir, args.clean)
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.info("Building JSON metadata...")
        build_creator_json_files(input_dir, config["media_rules"])
        
        logging.info("Building HTML site...")
        index_html_path = build_html_pages(input_dir, output_dir, config["html_settings"])
        
        if args.open:
            logging.info("Opening index.html...")
            webbrowser.open(f"file://{index_html_path.resolve()}")
        
    elif args.command == "print-config":
        config = _load_config(args.config)

        config = cfg.apply_cli_overrides(
            config,
            image_sample_strategy=ImageSampleStrategy(args.image_sample_strategy) if args.image_sample_strategy else None,
            portrait_strategy=PortraitStrategy(args.portrait_strategy) if args.portrait_strategy else None,
            domain=Domain(args.domain) if args.domain else None
        )

        print(json.dumps(config, indent=4))
        
    elif args.command == "clean-json":
        input_dir = _validate_input_dir(args.input)
        if input_dir is None:
            return

        if not args.force and not args.dry_run:
            confirm = input(f"Delete all cr4te.json files in '{input_dir}'? {YES_NO_STR}: ").strip().lower()
            if confirm != 'y':
                logging.info("Aborting.")
                return

        clean_creator_json_files(input_dir, dry_run=args.dry_run)

if __name__ == "__main__":
    main()

