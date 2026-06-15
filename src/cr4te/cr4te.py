import logging
import argparse
import webbrowser
import json
import sys
from enum import IntEnum
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

from .build_issues import BuildIssueError
from .build_runner import BuildPhaseError, BuildRequest, run_build
from .build_summary import log_build_summary
from .config_manager import load_config, apply_cli_overrides
from .schemas.config_schema import AppConfig
from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.portrait_discovery import PortraitDiscovery
from .enums.portrait_visibility import PortraitVisibility
from .enums.domain import Domain
from .metadata_manager import clean_metadata_files

# Short flags
FLAG_INPUT_SHORT = "-i"
FLAG_OUTPUT_SHORT = "-o"

# Long Flags
FLAG_INPUT = "--input"
FLAG_OUTPUT = "--output"
FLAG_OPEN = "--open"
FLAG_FORCE = "--force"
FLAG_CLEAN = "--clean"
FLAG_THEMES_DIR = "--themes-dir"


class ExitCode(IntEnum):
    SUCCESS = 0
    BUILD_FAILURE = 1


class CommandUsageError(ValueError):
    pass


def _setup_logging():
    """Configures the global logging settings."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr
    )

def _load_config(rel_config_path_arg: str | None) -> AppConfig:
    if not rel_config_path_arg:
        return load_config()

    config_path = Path(rel_config_path_arg).resolve()
    if not config_path.is_file():
        raise CommandUsageError(f"Config path does not exist or is not a file: {config_path}")
    try:
        return load_config(config_path)
    except (OSError, ValueError) as exc:
        raise CommandUsageError(f"Unable to load config file {config_path}: {exc}") from exc
    
def _confirm_action(prompt: str, force: bool = False) -> bool:
    if force:
        return True
    confirm = input(f"{prompt} [y/N]: ").strip().lower()
    return confirm == 'y'

def _domain_from_args(args) -> Domain | None:
    return Domain(args.domain) if args.domain else None

def _apply_cli_overrides_from_args(config: AppConfig, args) -> AppConfig:
    try:
        return apply_cli_overrides(
            config,
            image_sample_strategy=ImageSampleStrategy(args.image_sample_strategy) if args.image_sample_strategy else None,
            portrait_discovery=PortraitDiscovery(args.portrait_discovery) if args.portrait_discovery else None,
            portrait_visibility=PortraitVisibility(args.portrait_visibility) if args.portrait_visibility else None,
            domain=_domain_from_args(args)
        )
    except ValueError as exc:
        raise CommandUsageError(f"Invalid configuration override: {exc}") from exc

def _validate_input_dir(input_dir: Path) -> None:
    if not input_dir.is_dir():
        raise CommandUsageError(f"Input path does not exist or is not a directory: {input_dir}")


def _validate_build_paths(input_dir: Path, output_dir: Path) -> None:
    if input_dir == output_dir:
        raise CommandUsageError(f"Input and output paths must be different: {input_dir}")
    if output_dir.is_relative_to(input_dir):
        raise CommandUsageError(f"Output path must not be inside the input path: {output_dir} is inside {input_dir}")
    if input_dir.is_relative_to(output_dir):
        raise CommandUsageError(f"Output path must not contain the input path: {input_dir} is inside {output_dir}")


def _resolve_optional_directory(path_arg: str | None, label: str) -> Path | None:
    if not path_arg:
        return None
    path = Path(path_arg).resolve()
    if not path.is_dir():
        raise CommandUsageError(f"{label} does not exist or is not a directory: {path}")
    return path


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Media Organizer CLI")
    
    try:
        __version__ = version("cr4te")
    except PackageNotFoundError:
        __version__ = "0.0.0"
    
    parser.add_argument("-v", "--version", action="version", version=f"cr4te v{__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_config_arguments(p: argparse.ArgumentParser):
        p.add_argument("--config", help="Path to configuration file (optional)")
        p.add_argument("--domain", choices=[m.value for m in Domain], help="Apply a domain-specific configuration preset")
        p.add_argument("--image-sample-strategy", choices=[s.value for s in ImageSampleStrategy], help="Strategy to sample images per folder")
        p.add_argument("--portrait-discovery", choices=[mode.value for mode in PortraitDiscovery], help="Control portrait discovery")
        p.add_argument("--portrait-visibility", choices=[mode.value for mode in PortraitVisibility], help="Control where portraits are rendered")

    # Build subcommand
    build_parser = subparsers.add_parser("build", help="Scan metadata and build HTML site")
    build_parser.add_argument(FLAG_INPUT_SHORT, FLAG_INPUT, required=True, help="Path to the Creators folder")
    build_parser.add_argument(FLAG_OUTPUT_SHORT, FLAG_OUTPUT, required=True, help="Path to the HTML output folder")
    _add_config_arguments(build_parser)
    build_parser.add_argument(FLAG_OPEN, action="store_true", help="Open index.html after building")
    build_parser.add_argument(FLAG_FORCE, action="store_true", help="Force delete output folder")
    build_parser.add_argument(FLAG_CLEAN, action="store_true", help=f"Also delete thumbnails folder (with {FLAG_FORCE})")
    build_parser.add_argument(FLAG_THEMES_DIR, help="Path to a folder containing custom theme CSS files")
    build_parser.add_argument("--strict", action="store_true", help="Fail immediately on invalid metadata instead of skipping entries")

    # Print-config
    print_config_parser = subparsers.add_parser("print-config", help="Print resolved configuration")
    _add_config_arguments(print_config_parser)

    # Clean-json
    clean_parser = subparsers.add_parser("clean-json", help="Delete creator and project cr4te.json metadata files")
    clean_parser.add_argument(FLAG_INPUT_SHORT, FLAG_INPUT, required=True, help="Path to input folder containing creators")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without removing anything")
    clean_parser.add_argument(FLAG_FORCE, action="store_true", help="Actually delete files instead of showing a preview")

    return parser
    
def _build_cmd_handler(args) -> int:
    config = _load_config(args.config)
    config = _apply_cli_overrides_from_args(config, args)

    input_dir = Path(args.input).resolve()
    _validate_input_dir(input_dir)

    output_dir = Path(args.output).resolve()
    _validate_build_paths(input_dir, output_dir)

    custom_themes_dir = _resolve_optional_directory(getattr(args, "themes_dir", None), "Custom themes path")

    if output_dir.exists():
        msg = (
            f"Output folder '{output_dir}' exists. "
            f"Delete everything {'INCLUDING thumbnails' if args.clean else 'except thumbnails'}?"
        )
        if not _confirm_action(msg, force=args.force):
            logging.info("Aborting.")
            return ExitCode.SUCCESS

    result = run_build(
        BuildRequest(
            input_dir=input_dir,
            output_dir=output_dir,
            config=config,
            custom_themes_dir=custom_themes_dir,
            clear_thumbnails=args.clean,
            strict=args.strict,
        )
    )
    log_build_summary(result.summary, logging.getLogger(__name__))

    if args.open:
        logging.info("Opening index.html...")
        webbrowser.open(_file_uri(result.index_html_path))

    return ExitCode.SUCCESS


def _print_config_cmd_handler(args) -> int:
    config = _load_config(args.config)
    config = _apply_cli_overrides_from_args(config, args)
    print(json.dumps(config.model_dump(mode="json"), indent=4))
    return ExitCode.SUCCESS


def _clean_json_cmd_handler(args) -> int:
    input_dir = Path(args.input).resolve()
    _validate_input_dir(input_dir)

    if not args.dry_run and not _confirm_action(f"Delete all creator and project cr4te.json files in '{input_dir}'?", force=args.force):
        logging.info("Aborting.")
        return ExitCode.SUCCESS

    clean_metadata_files(input_dir, dry_run=args.dry_run)
    return ExitCode.SUCCESS


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    
    parser = _create_parser()
    args = parser.parse_args(argv)
    
    command_map = {
        "build": _build_cmd_handler,
        "print-config": _print_config_cmd_handler,
        "clean-json": _clean_json_cmd_handler,
    }
    
    command_func = command_map.get(args.command)
    if not command_func:
        parser.print_help()
        return ExitCode.SUCCESS
    
    try:
        return command_func(args)
    except (BuildIssueError, BuildPhaseError) as exc:
        logging.error(str(exc))
        return ExitCode.BUILD_FAILURE
    except CommandUsageError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())

