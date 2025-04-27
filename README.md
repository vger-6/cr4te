# cr4te

A static site generator for organizing and showcasing creative media projects. It scans your folder structure, extracts metadata and media, and builds a clean, searchable HTML gallery using Jinja2 templates.

---

## Features

- **Automatically builds a gallery website** from your folder of creators and projects
- **Thumbnail generation** for portraits, posters, and images
- **Tag-based filtering** and search
- **Flexible media grouping via regex rules**
- **Video and image organization with dynamic labels**
- **Build modes (flat, hybrid, deep) for customizable media discovery**
- **Jinja2 templating for fast, maintainable static HTML**
- **User-customizable labels and media rules** via optional config file
- **Fast static HTML output** with no runtime dependencies during browsing

---

## Folder Structure

```
Creators/
├── Alice/
│   ├── cr4te.json           # Optional metadata override
│   ├── README.md            # Optional creator description
|   ├── Portrait1.jpg
│   └── Project1/
│       ├── Landscape1.jpg
│       ├── clip.mp4
│       ├── README.md        # Optional project description
│       └── SubGroup/
│           └── *.jpg
└── Bob & Charlie/           # Collaboration folder
    └── ProjectZ/
```

---

## Installation

```bash
git clone https://github.com/yourname/cr4te.git
cd cr4te
pip install -r requirements.txt
```

---

## Usage

### Step 1: Build JSON metadata

```bash
python cr4te.py build-json -i /path/to/Creators --mode hybrid
```

Modes available:
- `flat` — Only media directly under the project root
- `hybrid` (default) — Flat .mp4 + first-level .jpg grouping
- `deep` — Find .mp4 and .jpg recursively

### Step 2: Generate HTML site

```bash
python cr4te.py build-html -i /path/to/Creators -o /path/to/OutputFolder
```

### Optional: Custom Configuration

```bash
python cr4te.py build-html -i /path/to/Creators -o /path/to/OutputFolder --config config/cr4te_config.json
```

---

## Media Discovery Logic

Media is discovered using regular expressions defined in the config:

### Global Exclusions

- Any file or folder whose name starts with `_`

### Videos

- **Included:** `.mp4` files (based on selected mode)
- **Excluded:** (none by default)

### Images

- **Included:** `.jpg` files (based on selected mode)
- **Excluded:** (none by default)

> Files are grouped into `media_groups` with intelligent dynamic labels based on structure and content type.

---

## Configuration

You can optionally supply a JSON configuration file to customize:

- **Creator and Project labels**
- **Regex patterns for media grouping and exclusion**

Example `cr4te_config.json`:

```json
{
  "html_settings": {
    "creator_label": "Director",
    "project_label": "Movie"
  },
  "media_rules": {
    "GLOBAL_EXCLUDE_RE": "(^|/|\\\\)_",
    "VIDEO_INCLUDE_RE": ".*\\.mp4$",
    "VIDEO_EXCLUDE_RE": "$^",
    "IMAGE_INCLUDE_RE": ".*\\.jpg$",
    "IMAGE_EXCLUDE_RE": "$^"
  }
}
```

If no `--config` is specified, cr4te uses internal defaults. If `config/cr4te_config.json` exists, it will be auto-loaded.

---

## Output Example

- `index.html` — Creator overview page
- `creators/<creator>.html` — Individual creator profiles
- `projects/<project>.html` — Individual project pages
- `tags.html` — Browse by tags

Thumbnails are automatically generated into `/thumbnails/`.

---

## Requirements

- Python 3.8+
- Pillow
- Markdown
- Jinja2

Install via:

```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the terms of the LICENSE file included.

---

## Credits

Created for artists, curators, media historians, and creative developers who want simple but structured control over their digital media archives.


