---
name: xinbada-alibaba-product-import
description: Extract product titles, detail copy, specification tables, and gallery images from Alibaba product links in CSV import sheets; transform the supplied HTML template into English-only Xinbada product content; generate title, remark, pro_fields, SEO, and file-name fields; replace visible Lifeworth branding; convert and compress images to WebP; upload images to ImgBB by API; fill thumb, scenario_image, and images with ImgBB direct links; and validate the completed import file. Use for Xinbada Alibaba-to-CSV product migrations with link, template, content, title, remark, pro_fields, seo_title1, seo_desc, file_name, thumb, scenario_image, and images fields.
---

# Xinbada Alibaba Product Import

Process every populated row independently. Preserve source facts, template structure, and protected company content exactly.

## Required resources

- Read [references/schema-and-guardrails.md](references/schema-and-guardrails.md) before editing a table.
- Use [assets/content_import_template.csv](assets/content_import_template.csv) when the user needs a fresh import sheet.
- Run `scripts/convert_images_to_webp.py` to create compressed WebP gallery images.
- Run `scripts/upload_images_to_imgbb.py` to upload WebP images and capture Direct links.
- Run `scripts/validate_output.py` against the completed CSV before delivery.

## Workflow

### 1. Inspect the table

1. Identify the input CSV and verify its headers.
2. Preserve the original file. Save to `<input-stem>_completed.csv` unless the user explicitly requests in-place editing or another output path.
3. Preserve `link`, `template`, and unknown columns unless the user requests changes. Generate `thumb`, `scenario_image`, and `images`.
4. Process only rows with both `link` and `template`.

### 2. Collect source facts

1. Open each Alibaba URL from `link`, preferring browser or Chrome control for dynamic content.
2. Capture only facts visible on that product page:
   - source product title;
   - product-detail text;
   - specification or attribute-table key/value pairs;
   - supplement facts, ingredients, serving size, count, flavor, net weight, benefits, certifications, and packaging when present;
   - ordered product-gallery image URLs.
3. Keep source units and numbers exact. Do not infer missing claims or copy facts from a similar product.
4. If the page is inaccessible or key facts cannot be verified, leave the row ungenerated and report the row and blocker.

### 3. Build `content`

1. Start from the row's `template` value, not from newly written HTML.
2. Write product-facing copy in polished English using the collected facts.
3. Preserve the following byte-for-byte where practical:
   - the complete `<style>` block;
   - HTML classes, element order, nesting, layout, spacing behavior, and colors;
   - the complete `.pd_story_feature` company-introduction article text and markup, except its image `src`.
4. Replace only product-specific text in editable modules. Change every product-facing occurrence of `Lifeworth` or `LIFEWORTH` to `Xinbada`; do not alter source URLs in `link`.
5. Use the brand `Xinbada` and company name `Xinbada Industrial (Shenzhen) Group Co., Ltd.`
6. Replace the existing FAQ content with exactly six distinct, fact-grounded question-and-answer items. Keep the FAQ grid markup, item numbering `01` through `06`, styles, and layout.
7. Keep the same number and order of `<img>` elements as the template. Replace their `src` values only after ImgBB upload.
8. Keep the HTML self-contained: do not add JavaScript, external fonts, page-level CSS, markdown, or local image paths.

### 4. Generate import fields

Generate all values in English only. Do not include Chinese characters in any generated field, including `content`.

- `title`: Use `Xinbada` + commercial product name + relevant OEM/ODM, flavor, form, or category terms. Keep it readable and fact-grounded.
- `remark`: Write one or two concise sentences describing the formula, serving or pack facts, use positioning, and private-label relevance.
- `pro_fields`: Write 4–8 separate plain-text lines with no leading bullet, dot, dash, or numbering. Include only verified differentiators and specifications.
- `file_name`: Convert the title to a lowercase ASCII kebab-case slug without an extension. Keep meaningful product and private-label keywords.
- `seo_title1`: Copy `title` exactly.
- `seo_desc`: Copy `remark` exactly.

### 5. Rebrand gallery images

1. Download every ordered gallery image from the Alibaba product page.
2. Inspect each image. Invoke `$imagegen` for image editing when visible `Lifeworth` branding appears.
3. Replace only the visible brand text/logo with `Xinbada`. Preserve the product, label geometry, typography character, colors, lighting, composition, aspect ratio, and resolution as closely as possible.
4. Keep downloads and edited source files in a temporary staging directory with ordered stems such as `01`, `02`, and so on.
5. Convert every final image to compressed WebP with quality `82` and method `6`. Preserve pixel dimensions, aspect ratio, orientation, and transparency; strip unnecessary metadata.
6. Write only `.webp` files under `images/<file_name>/` beside the output table. Use ordered names such as `01.webp`, `02.webp`, and so on. Do not leave JPEG, PNG, AVIF, GIF, or other source formats in the final product folder.
7. Keep the final local WebP files available until all ImgBB uploads and table validation succeed.

Run:

```bash
python3 scripts/convert_images_to_webp.py \
  /absolute/path/to/staged/product-images \
  --output-dir /absolute/path/to/images/<file_name> \
  --quality 82 \
  --method 6
```

Use this image-edit prompt as a starting point:

> Replace every visible “Lifeworth” brand word or logo with “Xinbada”. Preserve all other label text, product details, colors, materials, lighting, perspective, composition, aspect ratio, and resolution. Make no other design changes.

### 6. Upload images to ImgBB and fill image fields

1. Read the ImgBB API key from `IMGBB_API_KEY`. Never print it, pass it as a command-line argument, write it to a file, or commit it.
2. If `IMGBB_API_KEY` is missing, stop before upload and ask the user to set it in the environment.
3. Upload every final WebP through ImgBB API v1 with `POST https://api.imgbb.com/1/upload`. Do not set an expiration.
4. Use only `data.url` from each successful response. Accept only HTTPS Direct links on `i.ibb.co`; do not use viewer, thumbnail, medium, delete, or Markdown links.
5. Classify the uploaded images by visual role:
   - `thumb`: the single product-cover Direct link.
   - `scenario_image`: the single scene or lifestyle-image Direct link, stored as a plain URL without Markdown brackets.
   - `images`: all product-gallery Direct links in display order, one per line as `<url>|<English alt text>`.
6. Keep every alt text concise, descriptive, product-specific, and English only.
7. Replace every existing image `src` inside `content` with a suitable uploaded Direct link from the row:
   - use the cover image for the hero/product-overview module;
   - use the scene image for lifestyle, use-case, or scenario modules;
   - use matching product, formula, supplement-facts, factory, laboratory, or certification images for corresponding modules;
   - preserve the original image count, order, surrounding markup, CSS, and protected company text.
8. Use only links already written to `thumb`, `scenario_image`, or `images`. Do not retain old template image URLs or insert an unrelated image merely to fill a slot.

Run:

```bash
python3 scripts/upload_images_to_imgbb.py \
  /absolute/path/to/images/<file_name> \
  --manifest /absolute/path/to/upload-manifests/<file_name>.json
```

Do not write any image field until every required upload succeeds.

### 7. Validate and deliver

Run:

```bash
python3 scripts/validate_output.py /absolute/path/to/output.csv \
  --images-dir /absolute/path/to/images \
  --require-images
```

Fix every error before delivery. Review warnings against the source page. Report the output table path, processed row count, image-folder paths, and any skipped rows.

## Quality rules

- Prefer exact source facts over persuasive embellishment.
- Keep every generated field entirely in English; reject and rewrite any Chinese text.
- Avoid disease-treatment claims, unsupported performance promises, and unsupported certifications.
- Keep product naming consistent across `title`, `content`, FAQ, `pro_fields`, image alt text, and image-folder slug.
- Keep every delivered gallery image in compressed WebP format.
- Use ImgBB `data.url` Direct links for `thumb`, `scenario_image`, and `images`.
- Replace every `content` image `src` with a contextually suitable Direct link from those image fields while preserving the template structure.
- Never persist the ImgBB API key in a table, manifest, source file, log, or Git history.
- Escape CSV fields correctly; HTML may contain commas, quotes, and newlines.
- Preserve row order and UTF-8 encoding.
