import argparse
import json
import shutil

from pathlib import Path
from html_builder import build_html_pages
from json_builder import process_all_creators
from utils import is_valid_entry

def main():
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    subparsers = parser.add_subparsers(dest="command")
    json_parser = subparsers.add_parser("build-json", help="Generate JSON metadata from media folders")
    json_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    html_parser = subparsers.add_parser("build-html", help="Generate HTML site from JSON metadata")
    html_parser.add_argument("-i", "--input", required=True, help="Path to the Creators folder")
    args = parser.parse_args()

    if args.command == "build-json":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return
        process_all_creators(input_path)

    elif args.command == "build-html":
        input_path = Path(args.input).resolve()
        if not input_path.exists() or not input_path.is_dir():
            print(f"Input path does not exist or is not a directory: {input_path}")
            return

        output_path = Path.cwd() / "site_output"
        if output_path.exists():
            confirm = input(f"Output folder '{output_path}' already exists. Delete everything except thumbnails and rebuild? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborting.")
                return
            for item in output_path.iterdir():
                if item.name != "thumbnails":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        else:
            output_path.mkdir(parents=True, exist_ok=True)

        creator_data = []
        for creator in sorted(input_path.iterdir()):
            if not creator.is_dir() or not is_valid_entry(creator):
                continue
            json_path = creator / "cr4te.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    creator_data.append(json.load(f))

        build_html_pages(creator_data, output_path, input_path)

if __name__ == "__main__":
    main()

