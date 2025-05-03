# cr4te

A static site generator for organizing and showcasing creative media projects. It scans your folder structure, extracts metadata and media, and builds a clean, searchable HTML gallery using Jinja2 templates.

---

## Features

* **Automatically builds a gallery website** from your folder of creators and projects
* **Thumbnail generation** for portraits, posters, and images
* **Tag-based filtering** and search
* **Flexible media grouping via regex rules**
* **Video and image organization with dynamic labels**
* **Build modes (flat, hybrid, deep) for customizable media discovery**
* **Jinja2 templating for fast, maintainable static HTML**
* **User-customizable labels and media rules** via optional config file
* **Fast static HTML output** with no runtime dependencies during browsing

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

* `flat` — Only media directly under the project root
* `hybrid` (default) — Flat .mp4 + first-level .jpg grouping
* `deep` — Find .mp4 and .jpg recursively

### Step 2: Generate HTML site

```bash
python cr4te.py build-html -i /path/to/Creators -o /path/to/OutputFolder
```

### Optional: Custom Configuration

```bash
python cr4te.py build-html -i /path/to/Creators -o /path/to/OutputFolder --config config/cr4te_config.json
```

If `--config` is not specified, cr4te uses internal defaults.

---

## Configuration

Your configuration file should be in JSON format and can override labels and media matching rules:

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
    "IMAGE_EXCLUDE_RE": "$^",
    "MAX_IMAGES": 20,
    "IMAGE_SAMPLE_STRATEGY": "spread"
  }
}
```

The `IMAGE_SAMPLE_STRATEGY` can be one of:

* `spread`: even sampling throughout the list
* `head`: take the first N images

Regex patterns are compiled automatically using the `config.compile_media_rules` utility.

---

## Output Example

* `index.html` — Creator overview page
* `creators/<creator>.html` — Individual creator profiles
* `projects/<project>.html` — Individual project pages
* `tags.html` — Browse by tags

Thumbnails are automatically generated into `/thumbnails/`.

---

## Requirements

* Python 3.8+
* Pillow
* Markdown
* Jinja2

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the terms of the LICENSE file included.

---

## Credits

Created for artists, curators, media historians, and creative developers who want simple but structured control over their digital media archives.

