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
