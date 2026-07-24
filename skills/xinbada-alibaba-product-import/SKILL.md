---
name: xinbada-alibaba-product-import
description: Extract product titles, detail copy, specification tables, and gallery images from Alibaba product links in CSV import sheets; transform the supplied HTML template into English Xinbada product content; generate title, remark, parameter, SEO, and file-name fields; replace visible Lifeworth branding in gallery images; and validate the completed import file. Use for Xinbada Alibaba-to-CSV product migrations, especially tables containing the fields link, template, content, title, remark, parameter, seo_title1, seo_desc, and file_name.
---

# Xinbada Alibaba Product Import

Process every populated row independently. Preserve source facts, template structure, and protected company content exactly.

## Required resources

- Read [references/schema-and-guardrails.md](references/schema-and-guardrails.md) before editing a table.
- Use [assets/content_import_template.csv](assets/content_import_template.csv) when the user needs a fresh import sheet.
- Run `scripts/validate_output.py` against the completed CSV before delivery.

## Workflow

### 1. Inspect the table

1. Identify the input CSV and verify its headers.
2. Preserve the original file. Save to `<input-stem>_completed.csv` unless the user explicitly requests in-place editing or another output path.
3. Preserve `link`, `template`, `thumb`, and unknown columns unless the user requests changes.
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
   - every existing template image `src`, including the image in the first `.pd_section.is_soft`;
   - the complete `.pd_story_feature` company-introduction article, including its image and all text.
4. Replace only product-specific text in editable modules. Change every product-facing occurrence of `Lifeworth` or `LIFEWORTH` to `Xinbada`; do not alter source URLs in `link`.
5. Use the brand `Xinbada` and company name `Xinbada Industrial (Shenzhen) Group Co., Ltd.`
6. Replace the existing FAQ content with exactly six distinct, fact-grounded question-and-answer items. Keep the FAQ grid markup, item numbering `01` through `06`, styles, and layout.
7. Keep the HTML self-contained: do not add JavaScript, external fonts, page-level CSS, markdown, or local image paths.

### 4. Generate import fields

Generate all values in English:

- `title`: Use `Xinbada` + commercial product name + relevant OEM/ODM, flavor, form, or category terms. Keep it readable and fact-grounded.
- `remark`: Write one or two concise sentences describing the formula, serving or pack facts, use positioning, and private-label relevance.
- `parameter`: Write 4–8 separate lines, each beginning with `• `. Include only verified differentiators and specifications.
- `file_name`: Convert the title to a lowercase ASCII kebab-case slug without an extension. Keep meaningful product and private-label keywords.
- `seo_title1`: Copy `title` exactly.
- `seo_desc`: Copy `remark` exactly.

Do not populate `thumb` unless the user supplies a mapping rule.

### 5. Rebrand gallery images

1. Download every ordered gallery image from the Alibaba product page.
2. Inspect each image. Invoke `$imagegen` for image editing when visible `Lifeworth` branding appears.
3. Replace only the visible brand text/logo with `Xinbada`. Preserve the product, label geometry, typography character, colors, lighting, composition, aspect ratio, and resolution as closely as possible.
4. Save every final gallery image, including unchanged images, under `images/<file_name>/` beside the output table. Use ordered names such as `01.webp`, `02.webp`, and so on; retain the source format when practical.
5. Do not replace the image URLs inside `content`; template image sources are immutable.

Use this image-edit prompt as a starting point:

> Replace every visible “Lifeworth” brand word or logo with “Xinbada”. Preserve all other label text, product details, colors, materials, lighting, perspective, composition, aspect ratio, and resolution. Make no other design changes.

### 6. Validate and deliver

Run:

```bash
python3 scripts/validate_output.py /absolute/path/to/output.csv \
  --images-dir /absolute/path/to/images \
  --require-images
```

Fix every error before delivery. Review warnings against the source page. Report the output table path, processed row count, image-folder paths, and any skipped rows.

## Quality rules

- Prefer exact source facts over persuasive embellishment.
- Avoid disease-treatment claims, unsupported performance promises, and unsupported certifications.
- Keep product naming consistent across `title`, `content`, FAQ, parameters, and image-folder slug.
- Escape CSV fields correctly; HTML may contain commas, quotes, and newlines.
- Preserve row order and UTF-8 encoding.
