# How-Tos

## Create Default Images

```
convert -size 360x270 xc:"#f0f0f0" -gravity center -font "DejaVu-Sans-Bold" -pointsize 48 -fill "#666666" -annotate +0+0 "Thumb" default_thumb.jpg
```

## Remove Alpha Channel

```
convert input.png -background white -alpha remove -alpha off output.png
```

## Find String in all Files

```
grep -rn . -e 'Search-String'
```

## Find Dead Code

Install the development tools into the active environment:

```
python -m pip install -e ".[dev]"
```

Run the focused checks:

```
python -m ruff check src tests --select F401,F841,F811,F821,F823
python -m pyflakes src tests
python -m vulture src tests --min-confidence 80
```

## dos2unix

```
dos2unix file.txt
```
