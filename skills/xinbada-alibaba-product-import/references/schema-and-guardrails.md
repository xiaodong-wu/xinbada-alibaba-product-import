# CSV schema and guardrails

## Field mapping

| Field | Rule |
|---|---|
| `link` | Alibaba source URL. Read only; preserve exactly. |
| `template` | Per-row HTML source template. Read only; preserve exactly. |
| `IMGBB_API_KEY` | Sensitive per-row ImgBB API key. Read only; preserve exactly and never expose it. |
| `content` | Completed HTML derived from `template`. |
| `title` | Xinbada English commercial product title. |
| `remark` | Concise English product description. |
| `pro_fields` | 4–8 verified plain-text lines without a leading bullet, dot, dash, or number. |
| `file_name` | Lowercase ASCII kebab-case slug without extension. |
| `seo_title1` | Exact copy of `title`. |
| `seo_desc` | Exact copy of `remark`. |
| `thumb` | One ImgBB Direct link for the product-cover WebP. |
| `scenario_image` | One ImgBB Direct link for the scene or lifestyle WebP; store a plain URL, not Markdown. |
| `images` | Ordered gallery lines formatted as `<ImgBB Direct link>|<English alt text>`. |

Required brand values:

- Brand: `Xinbada`
- Company: `Xinbada Industrial (Shenzhen) Group Co., Ltd.`

Language rule:

- Write every generated field in English only.
- Do not include Chinese characters in `title`, `remark`, editable parts of `content`, `seo_title1`, `seo_desc`, `file_name`, `pro_fields`, `thumb`, `scenario_image`, or `images`.
- Preserve the protected Product Details section byte-for-byte even if it contains legacy or non-English template text.
- Preserve `link` and `template` as source fields; do not translate or rewrite them.

## Template edit boundary

Treat the row's `template` as the canonical layout.

Keep unchanged:

- the complete `<style>` block;
- all classes, module order, nesting, layout, and colors;
- the complete Product Details `<section>` containing `.pd_story_feature`, including its heading, copy, company-introduction article, story tiles, image attributes, and original image links;
- the number and order of `<img>` elements.

Edit:

- product names, descriptions, specifications, benefits, formula facts, and product-facing tags outside the protected Product Details section;
- product-facing `Lifeworth` text outside the protected Product Details section, replacing it with `Xinbada`;
- the FAQ heading, introduction, and exactly six `.pd_faq_item` question/answer pairs.
- only the first two `<img src>` values, replacing each with a contextually suitable ImgBB Direct link from the row's image fields.

Preserve the third and every later `<img>` element exactly as supplied by `template`. Do not change its `src`, `alt`, attributes, or surrounding markup. Never insert new local paths, viewer links, or unrelated images into editable content.

## Content evidence rules

Accept facts from:

1. the Alibaba product title;
2. the product-detail body;
3. the specification/attribute table;
4. readable supplement-facts or packaging text in gallery images.

When sources conflict, prefer the specification table for structured product attributes and the readable label for serving facts. Record the conflict and avoid a stronger claim than the evidence supports.

Do not:

- import claims from unrelated or merely similar Alibaba listings;
- include Chinese text in any generated field outside the protected Product Details section;
- turn marketing language into medical claims;
- retain `Lifeworth` in generated product-facing copy outside the protected Product Details section;
- change any text, markup, attribute, or image link in the protected Product Details section;
- claim OEM/ODM customization details that are not present, except the supplied positioning that Xinbada provides private-label OEM/ODM service.

## Example field style

```text
title:
Xinbada Private Label Creatine HCl Powder OEM ODM Pineapple Flavored Sports Nutrition Supplement

remark:
A pineapple-flavored creatine hydrochloride powder featuring a compact 960mg serving and 750mg of Creatine HCl per serving. Designed for private label sports nutrition products focused on strength, power, high-intensity performance, and recovery.

pro_fields:
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

## ImgBB upload and field mapping

- Official API documentation: <https://api.imgbb.com/>
- Use `POST https://api.imgbb.com/1/upload` with multipart form data.
- Read the API key only from the current CSV row's `IMGBB_API_KEY` field.
- Require the field to be present and nonempty for every populated product row.
- Preserve the value in the user's CSV, but never print it, quote it, pass it on the command line, copy it to another field, write it to a manifest, or commit it.
- Enforce ImgBB's 32 MB maximum before sending each image.
- Upload WebP files without expiration.
- Read the Direct link from response field `data.url`.
- Accept only URLs with scheme `https`, host `i.ibb.co`, and a `.webp` path.
- Do not store or expose `delete_url`, the API key outside its source CSV field, or request bodies.
- Store `thumb` and `scenario_image` as one plain Direct URL each.
- Store `images` as newline-separated `<url>|<alt>` entries. Keep every alt value in English.
- Do not use ImgBB viewer links, Markdown links, local paths, or URLs from `thumb`/`medium` response objects.
- Replace only the first two `content` image sources with suitable URLs from `thumb`, `scenario_image`, or `images`.
- Preserve the template's image count and order.
- Keep the third and every later content image exactly as it appears in `template`, including all Product Details image sources and attributes.
