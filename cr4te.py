import argparse
import shutil

from pathlib import Path
from html_builder import clear_output_folder, collect_creator_data, build_html_pages
from json_builder import process_all_creators

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
            clear_output_folder(output_path)
        else:
            output_path.mkdir(parents=True, exist_ok=True)

        creator_data = collect_creator_data(input_path)

        build_html_pages(creator_data, output_path, input_path)

if __name__ == "__main__":
    main()

