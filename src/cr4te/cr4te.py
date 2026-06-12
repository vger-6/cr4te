import logging
import argparse
import webbrowser
import json
import sys
from time import perf_counter
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

from .build_issues import BuildIssueError
from .build_metrics import BuildTimings
from .build_summary import BuildSummary, log_build_summary
from .config_manager import load_config, apply_cli_overrides
from .schemas.config_schema import AppConfig
from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.portrait_discovery import PortraitDiscovery
from .enums.portrait_visibility import PortraitVisibility
from .enums.domain import Domain
from .html_builder import build_html_pages_streaming
from .library_builder import build_library_index, load_indexed_creator
from .metadata_manager import clean_metadata_files, reconcile_metadata_files
from .output_preparation import clear_output_folder
from .themes import discover_themes

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

def _setup_logging():
    """Configures the global logging settings."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr
    )

def _load_config(rel_config_path_arg: str) -> AppConfig:
    config_path = Path(rel_config_path_arg).resolve() if rel_config_path_arg else None
    return load_config(config_path)
    
def _confirm_action(prompt: str, force: bool = False) -> bool:
    if force:
        return True
    confirm = input(f"{prompt} [y/N]: ").strip().lower()
    return confirm == 'y'

def _domain_from_args(args) -> Domain | None:
    return Domain(args.domain) if args.domain else None

def _apply_cli_overrides_from_args(config: AppConfig, args) -> AppConfig:
    return apply_cli_overrides(
        config,
        image_sample_strategy=ImageSampleStrategy(args.image_sample_strategy) if args.image_sample_strategy else None,
        portrait_discovery=PortraitDiscovery(args.portrait_discovery) if args.portrait_discovery else None,
        portrait_visibility=PortraitVisibility(args.portrait_visibility) if args.portrait_visibility else None,
        domain=_domain_from_args(args)
    )

def _build_paths_are_safe(input_dir: Path, output_dir: Path) -> bool:
    if input_dir == output_dir:
        logging.info(f"Input and output paths must be different: {input_dir}")
        return False
    if output_dir.is_relative_to(input_dir):
        logging.info(f"Output path must not be inside the input path: {output_dir} is inside {input_dir}")
        return False
    if input_dir.is_relative_to(output_dir):
        logging.info(f"Output path must not contain the input path: {input_dir} is inside {output_dir}")
        return False
    return True


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
    
def _build_cmd_handler(args):
    config = _load_config(args.config)
    config = _apply_cli_overrides_from_args(config, args)

    input_dir = Path(args.input).resolve()
    if not input_dir.is_dir():
        logging.info(f"Input path does not exist or is not a directory: {input_dir}")
        logging.info("Aborting.")
        return

    output_dir = Path(args.output).resolve()
    if not _build_paths_are_safe(input_dir, output_dir):
        logging.info("Aborting.")
        return

    custom_themes_dir = Path(args.themes_dir).resolve() if getattr(args, "themes_dir", None) else None
    phase_started = perf_counter()
    logging.info("Discovering themes...")
    theme_registry = discover_themes(custom_themes_dir, strict=args.strict)
    theme_discovery_seconds = perf_counter() - phase_started

    if output_dir.exists():
        msg = (
            f"Output folder '{output_dir}' exists. "
            f"Delete everything {'INCLUDING thumbnails' if args.clean else 'except thumbnails'}?"
        )
        if not _confirm_action(msg, force=args.force):
            logging.info("Aborting.")
            return

    phase_started = perf_counter()
    if output_dir.exists():
        clear_output_folder(output_dir, args.clean)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    output_preparation_seconds = perf_counter() - phase_started

    project_facet_fields = config.site_rendering.project_metadata.configured_fields()

    phase_started = perf_counter()
    logging.info("Reconciling metadata...")
    metadata_result = reconcile_metadata_files(input_dir, config.media_rules, project_facet_fields=project_facet_fields)
    metadata_reconciliation_seconds = perf_counter() - phase_started
    logging.info(
        f"Metadata summary: created={len(metadata_result.created)}, "
        f"updated={len(metadata_result.updated)}, unchanged={len(metadata_result.unchanged)}, "
        f"skipped={len(metadata_result.skipped)}"
    )

    phase_started = perf_counter()
    logging.info("Indexing media library...")
    library_index = build_library_index(input_dir, config.media_rules, strict=args.strict)
    library_indexing_seconds = perf_counter() - phase_started

    phase_started = perf_counter()
    logging.info("Building HTML site...")
    try:
        html_result = build_html_pages_streaming(
            library_index,
            theme_registry,
            output_dir,
            config.site_labels,
            config.site_rendering,
            lambda summary: load_indexed_creator(
                library_index,
                summary,
                config.media_rules,
            ),
            strict=args.strict,
        )
    except BuildIssueError as exc:
        logging.error(str(exc))
        logging.info("Aborting.")
        raise SystemExit(1) from exc
    html_rendering_seconds = perf_counter() - phase_started

    log_build_summary(
        BuildSummary.from_library_index(
            library_index,
            additional_issues=(*theme_registry.issues, *html_result.issues),
            timings=BuildTimings(
                theme_discovery_seconds=theme_discovery_seconds,
                output_preparation_seconds=output_preparation_seconds,
                metadata_reconciliation_seconds=metadata_reconciliation_seconds,
                library_indexing_seconds=library_indexing_seconds,
                html_rendering_seconds=html_rendering_seconds,
            ),
            asset_statistics=html_result.asset_statistics,
        ),
        logging.getLogger(__name__),
    )

    if args.open:
        logging.info("Opening index.html...")
        webbrowser.open(_file_uri(html_result.index_html_path))
        
def _print_config_cmd_handler(args):
    config = _load_config(args.config)
    config = _apply_cli_overrides_from_args(config, args)
    print(json.dumps(config.model_dump(mode="json"), indent=4))

def _clean_json_cmd_handler(args):
    input_dir = Path(args.input).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        logging.info(f"Input path does not exist or is not a directory: {input_dir}")
        logging.info("Aborting.")
        return

    if not args.dry_run and not _confirm_action(f"Delete all creator and project cr4te.json files in '{input_dir}'?", force=args.force):
        logging.info("Aborting.")
        return

    clean_metadata_files(input_dir, dry_run=args.dry_run)


def main():
    _setup_logging()
    
    parser = _create_parser()
    args = parser.parse_args()
    
    command_map = {
        "build": _build_cmd_handler,
        "print-config": _print_config_cmd_handler,
        "clean-json": _clean_json_cmd_handler,
    }
    
    command_func = command_map.get(args.command)
    if not command_func:
        parser.print_help()
        return
    
    try:
        command_func(args)
    except ValueError as e:
        parser.error(str(e))

if __name__ == "__main__":
    main()

