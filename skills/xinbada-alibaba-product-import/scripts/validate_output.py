#!/usr/bin/env python3
"""Validate a completed Xinbada Alibaba product-import CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


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
    "parameter",
}
GENERATED_FIELDS = (
    "title",
    "remark",
    "content",
    "seo_title1",
    "seo_desc",
    "file_name",
    "parameter",
)
COMPANY_NAME = "Xinbada Industrial (Shenzhen) Group Co., Ltd."
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMG_SRC_RE = re.compile(
    r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL
)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
FAQ_RE = re.compile(
    r"<article\b[^>]*\bclass\s*=\s*([\"'])[^\"']*\bpd_faq_item\b[^\"']*\1",
    re.IGNORECASE,
)
PARAMETER_PREFIX_RE = re.compile(r"^\s*(?:[•●▪◦‣⁃*+-]|\d+[.)])\s*")
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


def class_element(html: str, class_name: str) -> str | None:
    """Return the first complete element containing class_name."""
    opener = re.compile(
        rf"<(?P<tag>[a-z][a-z0-9]*)\b"
        rf"(?=[^>]*\bclass\s*=\s*([\"'])[^\"']*\b{re.escape(class_name)}\b[^\"']*\2)"
        rf"[^>]*>",
        re.IGNORECASE,
    ).search(html)
    if not opener:
        return None

    tag = opener.group("tag")
    token_re = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.IGNORECASE)
    depth = 0
    for token in token_re.finditer(html, opener.start()):
        raw = token.group(0)
        if raw.startswith("</"):
            depth -= 1
            if depth == 0:
                return html[opener.start() : token.end()]
        elif not raw.rstrip().endswith("/>"):
            depth += 1
    return None


def image_sources(html: str) -> list[str]:
    return [match.group(2) for match in IMG_SRC_RE.finditer(html)]


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

    for field in GENERATED_FIELDS:
        value = row.get(field) or ""
        if not value.strip():
            add(errors, row_number, f"{field} is empty")
        elif CJK_RE.search(value):
            add(errors, row_number, f"{field} contains Chinese text; use English only")

    title = row.get("title") or ""
    remark = row.get("remark") or ""
    content = row.get("content") or ""
    slug = (row.get("file_name") or "").strip()
    parameters = (row.get("parameter") or "").splitlines()

    if row.get("seo_title1") != title:
        add(errors, row_number, "seo_title1 must exactly equal title")
    if row.get("seo_desc") != remark:
        add(errors, row_number, "seo_desc must exactly equal remark")
    if title and "Xinbada" not in title:
        add(errors, row_number, "title must include Xinbada")
    if slug and not SLUG_RE.fullmatch(slug):
        add(errors, row_number, "file_name must be lowercase ASCII kebab-case")

    parameter_lines = [line.strip() for line in parameters if line.strip()]
    if parameter_lines and not 4 <= len(parameter_lines) <= 8:
        add(errors, row_number, "parameter must contain 4–8 nonblank plain-text lines")
    for index, line in enumerate(parameter_lines, 1):
        if PARAMETER_PREFIX_RE.match(line):
            add(
                errors,
                row_number,
                f"parameter line {index} must not begin with a bullet, dash, or number",
            )

    if content:
        if COMPANY_NAME not in content:
            add(errors, row_number, "content is missing the required company name")
        if re.search(r"lifeworth", content, re.IGNORECASE):
            add(errors, row_number, "content still contains Lifeworth branding")

        template_style = STYLE_RE.search(template)
        content_style = STYLE_RE.search(content)
        if not template_style or not content_style:
            add(errors, row_number, "template or content is missing its style block")
        elif template_style.group(0) != content_style.group(0):
            add(errors, row_number, "style block differs from template")

        if image_sources(template) != image_sources(content):
            add(errors, row_number, "template image src values or order changed")

        protected_template = class_element(template, "pd_story_feature")
        protected_content = class_element(content, "pd_story_feature")
        if not protected_template or not protected_content:
            add(errors, row_number, "protected pd_story_feature block is missing")
        elif protected_template != protected_content:
            add(errors, row_number, "protected pd_story_feature block changed")

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
