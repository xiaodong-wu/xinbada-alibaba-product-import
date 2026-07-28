#!/usr/bin/env python3
"""Validate a completed Xinbada Alibaba product-import CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_HEADERS = {
    "title",
    "remark",
    "thumb",
    "content",
    "seo_title1",
    "seo_desc",
    "file_name",
    "link",
    "template",
    "IMGBB_API_KEY",
    "pro_fields",
    "scenario_image",
    "images",
}
GENERATED_FIELDS = (
    "title",
    "remark",
    "thumb",
    "content",
    "seo_title1",
    "seo_desc",
    "file_name",
    "pro_fields",
    "scenario_image",
    "images",
)
COMPANY_NAME = "Xinbada Industrial (Shenzhen) Group Co., Ltd."
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMG_SRC_RE = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*)([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL
)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
FAQ_RE = re.compile(
    r"<article\b[^>]*\bclass\s*=\s*([\"'])[^\"']*\bpd_faq_item\b[^\"']*\1",
    re.IGNORECASE,
)
PRO_FIELDS_PREFIX_RE = re.compile(r"^\s*(?:[•●▪◦‣⁃*+-]|\d+[.)])\s*")
IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
CJK_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]"
)


def element_ranges(html: str, tag: str) -> list[tuple[int, int]]:
    """Return balanced ranges for all elements with a given tag."""
    token_re = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.IGNORECASE)
    stack: list[int] = []
    ranges: list[tuple[int, int]] = []
    for token in token_re.finditer(html):
        raw = token.group(0)
        if raw.startswith("</"):
            if stack:
                ranges.append((stack.pop(), token.end()))
        elif not raw.rstrip().endswith("/>"):
            stack.append(token.start())
    return ranges


def product_details_section(html: str) -> str | None:
    """Return the complete section that contains pd_story_feature."""
    marker = re.search(
        r"<[a-z][a-z0-9]*\b"
        r"(?=[^>]*\bclass\s*=\s*([\"'])[^\"']*\bpd_story_feature\b[^\"']*\1)"
        r"[^>]*>",
        html,
        re.IGNORECASE,
    )
    if not marker:
        return None
    containing = [
        item
        for item in element_ranges(html, "section")
        if item[0] <= marker.start() < item[1]
    ]
    if not containing:
        return None
    start, end = min(containing, key=lambda item: item[1] - item[0])
    return html[start:end]


def image_sources(html: str) -> list[str]:
    return [match.group(3) for match in IMG_SRC_RE.finditer(html)]


def is_imgbb_webp_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and (parsed.hostname or "").lower() == "i.ibb.co"
        and parsed.path.lower().endswith(".webp")
        and not parsed.username
        and not parsed.password
    )


def add(errors: list[str], row_number: int, message: str) -> None:
    errors.append(f"row {row_number}: {message}")


def validate_row(
    row: dict[str, str],
    row_number: int,
    images_dir: Path | None,
    require_images: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    link = (row.get("link") or "").strip()
    template = row.get("template") or ""

    if not link and not template and not any((row.get(f) or "").strip() for f in GENERATED_FIELDS):
        warnings.append(f"row {row_number}: blank row skipped")
        return
    if not re.match(r"^https?://(?:[^/]+\.)?alibaba\.com/", link, re.IGNORECASE):
        add(errors, row_number, "link is not an Alibaba HTTP(S) URL")
    if not template.strip():
        add(errors, row_number, "template is empty")
        return
    if not (row.get("IMGBB_API_KEY") or "").strip():
        add(errors, row_number, "IMGBB_API_KEY is empty")

    content = row.get("content") or ""
    protected_content = product_details_section(content)
    for field in GENERATED_FIELDS:
        value = row.get(field) or ""
        if not value.strip():
            add(errors, row_number, f"{field} is empty")
        elif field == "content" and protected_content:
            editable_content = value.replace(protected_content, "", 1)
            if CJK_RE.search(editable_content):
                add(errors, row_number, f"{field} contains Chinese text; use English only")
        elif CJK_RE.search(value):
            add(errors, row_number, f"{field} contains Chinese text; use English only")

    title = row.get("title") or ""
    remark = row.get("remark") or ""
    slug = (row.get("file_name") or "").strip()
    pro_fields = (row.get("pro_fields") or "").splitlines()

    if row.get("seo_title1") != title:
        add(errors, row_number, "seo_title1 must exactly equal title")
    if row.get("seo_desc") != remark:
        add(errors, row_number, "seo_desc must exactly equal remark")
    if title and "Xinbada" not in title:
        add(errors, row_number, "title must include Xinbada")
    if slug and not SLUG_RE.fullmatch(slug):
        add(errors, row_number, "file_name must be lowercase ASCII kebab-case")

    pro_field_lines = [line.strip() for line in pro_fields if line.strip()]
    if pro_field_lines and not 4 <= len(pro_field_lines) <= 8:
        add(errors, row_number, "pro_fields must contain 4–8 nonblank plain-text lines")
    for index, line in enumerate(pro_field_lines, 1):
        if PRO_FIELDS_PREFIX_RE.match(line):
            add(
                errors,
                row_number,
                f"pro_fields line {index} must not begin with a bullet, dash, or number",
            )

    allowed_image_urls: set[str] = set()
    for field in ("thumb", "scenario_image"):
        value = (row.get(field) or "").strip()
        if value and not is_imgbb_webp_url(value):
            add(
                errors,
                row_number,
                f"{field} must be a plain ImgBB WebP Direct link on https://i.ibb.co/",
            )
        elif value:
            allowed_image_urls.add(value)

    gallery_lines = [
        line.strip() for line in (row.get("images") or "").splitlines() if line.strip()
    ]
    for index, line in enumerate(gallery_lines, 1):
        if "|" not in line:
            add(errors, row_number, f"images line {index} must use '<url>|<alt>'")
            continue
        url, alt = (part.strip() for part in line.split("|", 1))
        if not is_imgbb_webp_url(url):
            add(
                errors,
                row_number,
                f"images line {index} must use an ImgBB WebP Direct link",
            )
        else:
            allowed_image_urls.add(url)
        if not alt:
            add(errors, row_number, f"images line {index} has an empty alt value")
        elif CJK_RE.search(alt):
            add(errors, row_number, f"images line {index} alt must be English only")

    if content:
        if COMPANY_NAME not in content:
            add(errors, row_number, "content is missing the required company name")
        editable_content = (
            content.replace(protected_content, "", 1)
            if protected_content
            else content
        )
        if re.search(r"lifeworth", editable_content, re.IGNORECASE):
            add(errors, row_number, "content still contains Lifeworth branding")

        template_style = STYLE_RE.search(template)
        content_style = STYLE_RE.search(content)
        if not template_style or not content_style:
            add(errors, row_number, "template or content is missing its style block")
        elif template_style.group(0) != content_style.group(0):
            add(errors, row_number, "style block differs from template")

        template_images = image_sources(template)
        content_images = image_sources(content)
        if len(template_images) != len(content_images):
            add(
                errors,
                row_number,
                "content must preserve the template image count and order",
            )
        if len(content_images) < 2:
            add(errors, row_number, "content must contain at least two product images")
        for index, url in enumerate(content_images, 1):
            if index <= 2 and not is_imgbb_webp_url(url):
                add(
                    errors,
                    row_number,
                    f"content image {index} must be an ImgBB WebP Direct link",
                )
            elif index <= 2 and url not in allowed_image_urls:
                add(
                    errors,
                    row_number,
                    f"content image {index} is not listed in thumb, scenario_image, or images",
                )
            elif index > 2 and index <= len(template_images) and url != template_images[index - 1]:
                add(
                    errors,
                    row_number,
                    f"content image {index} must remain unchanged from template",
                )

        protected_template = product_details_section(template)
        if not protected_template or not protected_content:
            add(errors, row_number, "protected Product Details section is missing")
        elif protected_template != protected_content:
            add(
                errors,
                row_number,
                "protected Product Details section must remain byte-for-byte unchanged",
            )

        faq_count = len(FAQ_RE.findall(content))
        if faq_count != 6:
            add(errors, row_number, f"content has {faq_count} FAQ items; expected 6")

    if images_dir and slug:
        product_dir = images_dir / slug
        image_files: list[Path] = []
        if product_dir.is_dir():
            image_files = [
                path
                for path in product_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ]
        if not image_files:
            message = f"no gallery images found in {product_dir}"
            if require_images:
                add(errors, row_number, message)
            else:
                warnings.append(f"row {row_number}: {message}")
        else:
            non_webp = [path.name for path in image_files if path.suffix.lower() != ".webp"]
            if non_webp:
                add(
                    errors,
                    row_number,
                    "gallery folder contains non-WebP images: " + ", ".join(sorted(non_webp)),
                )
            for path in image_files:
                if path.suffix.lower() != ".webp":
                    continue
                try:
                    signature = path.read_bytes()[:12]
                except OSError as exc:
                    add(errors, row_number, f"cannot read gallery image {path.name}: {exc}")
                    continue
                if not (
                    len(signature) == 12
                    and signature[:4] == b"RIFF"
                    and signature[8:12] == b"WEBP"
                ):
                    add(errors, row_number, f"{path.name} is not a valid WebP file")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument(
        "--images-dir",
        type=Path,
        help="Base images directory containing one <file_name> folder per row",
    )
    parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail when a row has no image files in images/<file_name>/",
    )
    args = parser.parse_args()

    if args.require_images and args.images_dir is None:
        parser.error("--require-images requires --images-dir")
    if not args.csv_file.is_file():
        parser.error(f"CSV not found: {args.csv_file}")

    errors: list[str] = []
    warnings: list[str] = []
    with args.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_HEADERS - headers)
        if missing:
            errors.append("missing headers: " + ", ".join(missing))
        rows = list(reader)

    if not rows:
        errors.append("CSV contains no data rows")
    elif not (REQUIRED_HEADERS - headers):
        for number, row in enumerate(rows, start=2):
            validate_row(
                row,
                number,
                args.images_dir,
                args.require_images,
                errors,
                warnings,
            )

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK: {len(rows)} row(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
