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
from .metadata_manager import delete_metadata_files

# Short flags
FLAG_INPUT_SHORT = "-i"
FLAG_OUTPUT_SHORT = "-o"

# Long Flags
FLAG_INPUT = "--input"
FLAG_OUTPUT = "--output"
FLAG_OPEN = "--open"
FLAG_FORCE = "--force"
FLAG_CLEAR_THUMBNAIL_CACHE = "--clear-thumbnail-cache"
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
    parser = argparse.ArgumentParser(
        prog="cr4te",
        description="Build static sites for personal media libraries.",
        epilog="Run 'cr4te COMMAND --help' for command-specific options and examples.",
    )
    
    try:
        __version__ = version("cr4te")
    except PackageNotFoundError:
        __version__ = "0.0.0"
    
    parser.add_argument("-v", "--version", action="version", version=f"cr4te v{__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    def _add_config_arguments(p: argparse.ArgumentParser):
        p.add_argument("--config", help="Load configuration from FILE before applying CLI overrides", metavar="FILE")
        p.add_argument(
            "--domain",
            choices=[m.value for m in Domain],
            help="Apply a built-in domain preset after loading configuration",
        )
        p.add_argument(
            "--image-sample-strategy",
            choices=[s.value for s in ImageSampleStrategy],
            help="Override gallery sampling: none selects no images, head selects the first images, spread distributes selections, and all selects every image",
        )
        p.add_argument(
            "--portrait-discovery",
            choices=[mode.value for mode in PortraitDiscovery],
            help="Override portrait discovery: named uses basename matches; auto also permits orientation fallback",
        )
        p.add_argument(
            "--portrait-visibility",
            choices=[mode.value for mode in PortraitVisibility],
            help="Override portrait rendering: disabled hides portraits, details limits them to detail pages, and all includes overview cards",
        )

    # Build subcommand
    build_parser = subparsers.add_parser(
        "build",
        help="Reconcile metadata and build the static site",
        description="Reconcile library metadata and generate a static HTML site.",
        epilog="Example: cr4te build -i path/to/library -o path/to/site --domain music",
    )
    build_parser.add_argument(FLAG_INPUT_SHORT, FLAG_INPUT, required=True, help="Library root containing creator folders")
    build_parser.add_argument(FLAG_OUTPUT_SHORT, FLAG_OUTPUT, required=True, help="Folder for the generated static site")
    _add_config_arguments(build_parser)
    build_parser.add_argument(FLAG_OPEN, action="store_true", help="Open index.html after a successful build")
    build_parser.add_argument(FLAG_FORCE, action="store_true", help="Skip confirmation before replacing existing output")
    build_parser.add_argument(
        FLAG_CLEAR_THUMBNAIL_CACHE,
        action="store_true",
        help="Remove cached thumbnails before building",
    )
    build_parser.add_argument(FLAG_THEMES_DIR, help="Folder containing custom theme CSS files", metavar="DIR")
    build_parser.add_argument("--strict", action="store_true", help="Fail immediately on invalid metadata instead of skipping entries")
    build_parser.set_defaults(_command_parser=build_parser)

    # Print-config
    print_config_parser = subparsers.add_parser(
        "print-config",
        help="Print the resolved configuration",
        description="Print the fully resolved configuration after applying a file, domain preset, and CLI overrides.",
        epilog="Example: cr4te print-config --domain music",
    )
    _add_config_arguments(print_config_parser)
    print_config_parser.set_defaults(_command_parser=print_config_parser)

    # Delete metadata
    delete_metadata_parser = subparsers.add_parser(
        "delete-metadata",
        help="Delete creator and project metadata files",
        description="Delete cr4te.json metadata files below a library root. This does not delete media files.",
        epilog="Example: cr4te delete-metadata -i path/to/library --dry-run",
    )
    delete_metadata_parser.add_argument(
        FLAG_INPUT_SHORT,
        FLAG_INPUT,
        required=True,
        help="Library root containing creator folders",
    )
    delete_mode = delete_metadata_parser.add_mutually_exclusive_group()
    delete_mode.add_argument("--dry-run", action="store_true", help="List metadata files that would be deleted")
    delete_mode.add_argument(FLAG_FORCE, action="store_true", help="Skip deletion confirmation")
    delete_metadata_parser.set_defaults(_command_parser=delete_metadata_parser)

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
            f"Replace it and {'clear' if args.clear_thumbnail_cache else 'preserve'} the thumbnail cache?"
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
            clear_thumbnail_cache=args.clear_thumbnail_cache,
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


def _delete_metadata_cmd_handler(args) -> int:
    input_dir = Path(args.input).resolve()
    _validate_input_dir(input_dir)

    if not args.dry_run and not _confirm_action(f"Delete all creator and project cr4te.json files in '{input_dir}'?", force=args.force):
        logging.info("Aborting.")
        return ExitCode.SUCCESS

    delete_metadata_files(input_dir, dry_run=args.dry_run)
    return ExitCode.SUCCESS


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    
    parser = _create_parser()
    args = parser.parse_args(argv)
    
    command_map = {
        "build": _build_cmd_handler,
        "print-config": _print_config_cmd_handler,
        "delete-metadata": _delete_metadata_cmd_handler,
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
        args._command_parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())

