from pathlib import Path

# === General project structure ===
SCRIPT_DIR = Path(__file__).resolve().parents[1]

CR4TE_ASSETS_DIR = SCRIPT_DIR / "assets"
CR4TE_DEFAULTS_DIR = CR4TE_ASSETS_DIR / "defaults"
CR4TE_CSS_DIR = CR4TE_ASSETS_DIR / "css"
CR4TE_JS_DIR = CR4TE_ASSETS_DIR / "js"
CR4TE_TEMPLATES_DIR = SCRIPT_DIR / "templates"

# === Shared filenames ===
CR4TE_JSON_REL_PATH = ".cr4te/creator.json"

