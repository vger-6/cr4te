# cr4te

A static site generator for organizing and showcasing creative media projects. It scans your folder structure, extracts metadata and media, and builds a clean, searchable HTML gallery.

---

## Features

- **Automatically builds a gallery website** from your folder of creators and projects
- **Thumbnail generation** for portraits, posters, and images
- **Tag-based filtering** and search
- **Flexible media grouping via regex rules**
- **Fast static HTML output** with no runtime dependencies

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
│       └── SubGroup/
│           └── *.jpg
└── Bob & Charlie/             # Collaboration folder
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
python cr4te.py build-json -i /path/to/Creators
```

### Step 2: Generate HTML site
```bash
python cr4te.py build-html -i /path/to/Creators
```

> Output will be saved to `site_output/`.

---

## Media Discovery Logic

Media is discovered using regular expressions with full-path awareness:

### Global Exclusions
- Any file or folder containing segments that start with `_`

### Videos
- **Included:** `.mp4` files directly in the root of each project folder
- **Excluded:** (None by default)

### Images
- **Included:** `.jpg` files located in *immediate subfolders* of the project folder
- **Excluded:**
  - Filenames starting with `m` or `M`
  - Files inside any folder named `test`

> Files are grouped by their relative folder paths into labeled `media_groups` for organized display in the UI.

---

## Customization

- **Regex patterns** are hardcoded by now, but designed to be externalized to config in future
- **CSS styles** live in `css/`
- **Default thumbnails** are in `defaults/`
- You can override project metadata with `cr4te.json` inside each creator folder
- Add creator/project descriptions using `README.md`

---

## Output Example

- `index.html` — Creator overview
- `creators/<name>.html` — Creator profile
- `projects/<name>.html` — Individual project page
- `tags.html` — Browse all tags

---

## Requirements

- Python 3.8+
- Pillow
- Markdown

Install via:
```bash
pip install pillow markdown
```

---

## License

This project is licensed under the terms of the LICENSE file included.

---

## Credits

Created with love for artists, curators, media historians, and creative developers who want simple but structured control over their digital media archives.

---


