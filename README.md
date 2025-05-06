# cr4te

> **⚠️ Under Construction**
> This project is still in development. Features, structure, and configuration may change without notice.

A static site generator for organizing and showcasing creative media projects. It scans your folder structure, extracts metadata and media, and builds a clean, searchable HTML gallery using Jinja2 templates.

## Support This Project 🙏

If you find cr4te useful, consider [donating via PayPal](https://www.paypal.com/donate/?hosted_button_id=XERA3ZMTLZC2N) to help support continued development.

---

## Features

* **Automatically builds a gallery website** from your folder structure
* **Thumbnail generation** for portraits, posters, and images
* **Tag-based filtering** and search
* **Flexible media grouping via regex rules**
* **Video and image organization with dynamic labels**
* **Build modes (flat, hybrid, deep) for customizable media discovery**
* **Dedicated overview page for all projects with A-Z filter and tag-aware search**
* **HTML label presets for different domains** (directors, artists, ...)
* **Jinja2 templating for fast, maintainable static HTML**
* **User-customizable labels and media rules** via optional config file
* **Fast static HTML output** with no runtime dependencies during browsing

> This tool is an ongoing work-in-progress. Expect improvements, breaking changes, and new features.

---

## Folder Structure

```
Artists/
├── Alice/
│   ├── cr4te.json           # Optional metadata override
│   ├── README.md            # Optional description
|   ├── profile.jpg          # Detected portrait (via PORTRAIT_RE)
│   └── Project1/
│       ├── cover.jpg        # Detected poster (via POSTER_RE)
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
git clone https://github.com/vger-6/cr4te.git
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

### Optional: Apply a Label Preset

```bash
python cr4te.py build-html -i /path/to/Creators -o /path/to/OutputFolder --html-preset director
```

Available presets:

* `creator` (default)
* `director`
* `artist`
* `model`

If `--config` is not specified, cr4te uses internal defaults.

---

## Configuration

Your configuration file should be in JSON format and can override labels and media matching rules:

```json
{
  "html_settings": {
    "nav_creators_label": "Directors",
    "nav_projects_label": "Movies",
    "nav_tags_label": "Tags",

    "overview_page_title": "Directors",
    "overview_page_search_placeholder": "Search directors, movies, tags...",
    "project_overview_page_title": "Movies",
    "project_overview_page_search_placeholder": "Search movies, tags...",

    "creator_page_profile_title": "Profile",
    "creator_page_about_title": "About",
    "creator_page_tags_title": "Tags",
    "creator_page_projects_title": "Movies",
    "creator_page_collabs_title_prefix": "Codirected with",

    "collaboration_page_profile_title": "Profile",
    "collaboration_page_about_title": "About",
    "collaboration_page_tags_title": "Tags",
    "collaboration_page_members_title": "Members",
    "collaboration_page_projects_title": "Movies",

    "project_page_overview_title": "Overview",
    "project_page_description_title": "Description",
    "project_page_tags_title": "Tags",
    "project_page_creator_profile": "Profile",
    "project_page_videos_label": "Videos",
    "project_page_images_label": "Images"
  },
  "media_rules": {
    "GLOBAL_EXCLUDE_RE": "(^|/|\\\\)_",

    "VIDEO_INCLUDE_RE": ".*\\.mp4$",
    "VIDEO_EXCLUDE_RE": "$^",
    "IMAGE_INCLUDE_RE": ".*\\.jpg$",
    "IMAGE_EXCLUDE_RE": "$^",

    "PORTRAIT_RE": "^profile\\.jpg$",
    "POSTER_RE": "^cover\\.jpg$",

    "MAX_IMAGES": 20,
    "IMAGE_SAMPLE_STRATEGY": "spread"
  }
}
```

### Special Rules

* `PORTRAIT_RE`: Regex used to identify a creator's portrait image (default: `^profile\.jpg$`)
* `POSTER_RE`: Regex used to identify a project's poster image (default: `^cover\.jpg$`)
* `IMAGE_SAMPLE_STRATEGY`: Sampling strategy for gallery thumbnails

  * `spread`: even sampling throughout the list
  * `head`: take the first N images

---

## Output Example

* `index.html` — Creator overview page
* `projects.html` — All projects overview page
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

> Development is ongoing. Feedback, ideas, and contributions are very welcome!

