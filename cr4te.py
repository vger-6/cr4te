import sys
import argparse
import webbrowser
import json
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import config_manager as cfg
from enums.image_sample_strategy import ImageSampleStrategy
from enums.domain_preset import DomainPreset
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

    # build
    build_parser = subparsers.add_parser("build", help="Generate JSON metadata and build HTML site")
    build_parser.add_argument("-i", "--input", help="Path to the Creators folder")
    build_parser.add_argument("-o", "--output", help="Path to the HTML output folder")
    build_parser.add_argument("--config", help="Path to configuration file (optional)")
    build_parser.add_argument("--domain-preset", choices=[m.value for m in DomainPreset], help="Apply a common domain preset")
    build_parser.add_argument("--max-images", type=int, help="Maximum number of images to include per media group")
    build_parser.add_argument("--image-sample-strategy", choices=[s.value for s in ImageSampleStrategy], help="Strategy to sample images per folder")
    build_parser.add_argument("--auto-find-portraits", action="store_true", help="Search folders recursively to find a fitting portrait")
    build_parser.add_argument("--hide-portraits", action="store_true", help="Hide portraits on all pages")
    build_parser.add_argument('--open', action='store_true', help="Open index.html in the default browser after building.")
    build_parser.add_argument("--force", action="store_true", help="Delete the output folder and its contents (except thumbnails) without confirmation")
    build_parser.add_argument("--clean", action="store_true", help="Also delete the thumbnails folder (only valid with --force)")
    build_parser.add_argument("--print-config-only", action="store_true", help="Print adjusted configuration and exit (no file operations or build)")
    
    # clean-json
    clean_parser = subparsers.add_parser("clean-json", help="Delete cr4te.json files from all creator folders")
    clean_parser.add_argument("-i", "--input", required=True, help="Path to input folder containing creators")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without removing anything")
    clean_parser.add_argument("--force", action="store_true", help="Actually delete files instead of showing a preview")
    
    args = parser.parse_args()
    
    if args.command == "build":
        if not args.print_config_only:
            if not args.input:
                parser.error("argument -i/--input is required unless --print-config-only is used")
            if not args.output:
                parser.error("argument -o/--output is required unless --print-config-only is used")
                
        if args.auto_find_portraits and args.hide_portraits:
            print("[Warning] Both --auto-find-portraits and --hide-portraits are set. "
                  "Automatic portrait finding will still run, but portraits will not be shown in the output.",
                  file=sys.stderr)
                
        config = _load_config(args.config)
        
        config = cfg.apply_cli_overrides(
            config,
            image_gallery_max=args.max_images,
            image_sample_strategy=ImageSampleStrategy(args.image_sample_strategy) if args.image_sample_strategy else None,
            auto_find_portraits=args.auto_find_portraits,
            hide_portraits=args.hide_portraits,
            domain_preset=DomainPreset(args.domain_preset) if args.domain_preset else None
        )

        if args.print_config_only:
            # Only warn if output is not redirected
            if sys.stdout.isatty():
                ignored_flags = []
                if args.input:
                    ignored_flags.append("--input")
                if args.output:
                    ignored_flags.append("--output")
                if args.open:
                    ignored_flags.append("--open")
                if args.force:
                    ignored_flags.append("--force")
                if args.clean:
                    ignored_flags.append("--clean")
                
                if ignored_flags:
                    print(f"[Info] Ignoring flags: {', '.join(sorted(ignored_flags))} (no build performed).", file=sys.stderr)
        
            print(json.dumps(config, indent=4))
            return   
        
        if args.clean and not args.force:
            parser.error("--clean must be used together with --force")
        
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return
            
        output_path = Path(args.output).resolve()
        if output_path.exists():
            confirm = 'y' if args.force else input(f"Output folder '{output_path}' already exists. Delete everything except thumbnails and rebuild? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborting.")
                return
            clear_output_folder(output_path, args.clean)
        else:
            output_path.mkdir(parents=True, exist_ok=True)
        
        print("Building JSON metadata...")
        build_creator_json_files(input_path, config["media_rules"])
        
        print("Building HTML site...")
        html_index_path = build_html_pages(input_path, output_path, config["html_settings"])
        
        if args.open:
            print("Opening index.html...")
            webbrowser.open(f"file://{html_index_path.resolve()}")
        
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

if __name__ == "__main__":
    main()

