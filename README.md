# Xinbada Alibaba Product Import

A Codex skill that turns Alibaba product links in a CSV import sheet into Xinbada-ready product content.

It can:

- extract product titles, detail copy, specification tables, and gallery images;
- preserve the supplied HTML template, styling, image URLs, and protected company section;
- generate English-only product content, six FAQs, metadata, SEO fields, and file-name slugs without Chinese text;
- replace visible Lifeworth branding in gallery images with Xinbada;
- generate `parameter` as plain lines without leading bullet symbols;
- convert every gallery image to compressed WebP;
- validate the completed CSV before delivery.

## Install with Codex

Ask Codex:

```text
Use $skill-installer to install:
https://github.com/xiaodong-wu/xinbada-alibaba-product-import/tree/main/skills/xinbada-alibaba-product-import
```

Or run the bundled installer directly:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo xiaodong-wu/xinbada-alibaba-product-import \
  --path skills/xinbada-alibaba-product-import
```

The skill becomes available on the next Codex turn.

## Use

```text
Use $xinbada-alibaba-product-import to process this Alibaba product import CSV.
```

The skill preserves the source file by default and writes a completed copy. Rebranded gallery images are compressed at WebP quality 82 and saved under `images/<file_name>/` beside the output table.

## Repository layout

```text
skills/xinbada-alibaba-product-import/
├── SKILL.md
├── agents/openai.yaml
├── assets/content_import_template.csv
├── references/schema-and-guardrails.md
├── scripts/convert_images_to_webp.py
└── scripts/validate_output.py
```

Image conversion requires [Pillow](https://pypi.org/project/pillow/).

## Convert gallery images

```bash
python3 skills/xinbada-alibaba-product-import/scripts/convert_images_to_webp.py \
  /absolute/path/to/staged/product-images \
  --output-dir /absolute/path/to/images/<file_name> \
  --quality 82 \
  --method 6
```

## Validate

```bash
python3 skills/xinbada-alibaba-product-import/scripts/validate_output.py \
  /absolute/path/to/output.csv \
  --images-dir /absolute/path/to/images \
  --require-images
```

## License

Released under the [MIT License](LICENSE).
