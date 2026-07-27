# CSV schema and guardrails

## Field mapping

| Field | Rule |
|---|---|
| `link` | Alibaba source URL. Read only; preserve exactly. |
| `template` | Per-row HTML source template. Read only; preserve exactly. |
| `content` | Completed HTML derived from `template`. |
| `title` | Xinbada English commercial product title. |
| `remark` | Concise English product description. |
| `parameter` | 4–8 verified plain-text lines without a leading bullet, dot, dash, or number. |
| `file_name` | Lowercase ASCII kebab-case slug without extension. |
| `seo_title1` | Exact copy of `title`. |
| `seo_desc` | Exact copy of `remark`. |
| `thumb` | Preserve unless the user provides a rule. |

Required brand values:

- Brand: `Xinbada`
- Company: `Xinbada Industrial (Shenzhen) Group Co., Ltd.`

Language rule:

- Write every generated field in English only.
- Do not include Chinese characters in `title`, `remark`, `content`, `seo_title1`, `seo_desc`, `file_name`, or `parameter`.
- Preserve `link` and `template` as source fields; do not translate or rewrite them.

## Template edit boundary

Treat the row's `template` as the canonical layout.

Keep unchanged:

- the complete `<style>` block;
- every image `src` already in the template;
- all classes, module order, nesting, layout, and colors;
- the complete `<article class="pd_story_feature">…</article>` company introduction;
- gallery images as external files only; never insert their local paths into `content`.

Edit:

- product names, descriptions, specifications, benefits, formula facts, and product-facing tags;
- product-facing `Lifeworth` text, replacing it with `Xinbada`;
- the FAQ heading, introduction, and exactly six `.pd_faq_item` question/answer pairs.

The protected `.pd_story_feature` boundary resolves the source instruction about keeping the company-introduction image and text unchanged while still allowing the product-specific story tiles in the same larger section to be updated.

## Content evidence rules

Accept facts from:

1. the Alibaba product title;
2. the product-detail body;
3. the specification/attribute table;
4. readable supplement-facts or packaging text in gallery images.

When sources conflict, prefer the specification table for structured product attributes and the readable label for serving facts. Record the conflict and avoid a stronger claim than the evidence supports.

Do not:

- import claims from unrelated or merely similar Alibaba listings;
- include Chinese text in any generated field;
- turn marketing language into medical claims;
- retain `Lifeworth` in generated product-facing copy;
- change protected company text even to improve grammar;
- claim OEM/ODM customization details that are not present, except the supplied positioning that Xinbada provides private-label OEM/ODM service.

## Example field style

```text
title:
Xinbada Private Label Creatine HCl Powder OEM ODM Pineapple Flavored Sports Nutrition Supplement

remark:
A pineapple-flavored creatine hydrochloride powder featuring a compact 960mg serving and 750mg of Creatine HCl per serving. Designed for private label sports nutrition products focused on strength, power, high-intensity performance, and recovery.

parameter:
Superior solubility and high absorption rate
Less than 1g per serving for an effective compact serving format
Gentle on the stomach compared with creatine monohydrate
Supports enhanced strength, power, muscle volume, and high-intensity performance
Naturally flavored and sweetened with 64 servings per container

file_name:
xinbada-private-label-creatine-hcl-powder-oem-odm-pineapple-fast-absorption-sports-nutrition-supplement
```

Use the style, not unsupported facts, when processing other products.

## Gallery-image output

- Stage downloaded or rebranded images outside the final product folder.
- Convert all final images with `scripts/convert_images_to_webp.py`.
- Use WebP quality `82` and compression method `6` unless the user explicitly requests another quality.
- Preserve original pixel dimensions, aspect ratio, orientation, and transparency.
- Save only ordered `.webp` files in `images/<file_name>/`.
- Do not retain JPEG, PNG, AVIF, GIF, TIFF, BMP, or other source formats in the final folder.
