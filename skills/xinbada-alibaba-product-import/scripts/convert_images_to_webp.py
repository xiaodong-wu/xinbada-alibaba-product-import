#!/usr/bin/env python3
"""Convert product-gallery images to compressed WebP files."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print(
        "ERROR: Pillow is required. Install it with: python3 -m pip install Pillow",
        file=sys.stderr,
    )
    raise SystemExit(2)


SUPPORTED_EXTENSIONS = {
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


def bounded_integer(minimum: int, maximum: int):
    def parse(value: str) -> int:
        number = int(value)
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(
                f"must be between {minimum} and {maximum}"
            )
        return number

    return parse


def natural_key(path: Path) -> list[tuple[int, int | str]]:
    return [
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", path.name)
    ]


def collect_sources(paths: list[Path], recursive: bool) -> list[Path]:
    sources: list[Path] = []
    seen: set[Path] = set()

    for path in paths:
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            candidates = sorted(
                (
                    candidate
                    for candidate in iterator
                    if candidate.is_file()
                    and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
                ),
                key=natural_key,
            )
        else:
            raise ValueError(f"input does not exist: {path}")

        for candidate in candidates:
            if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"unsupported image format: {candidate}")
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                sources.append(candidate)

    if not sources:
        raise ValueError("no supported images found")
    return sources


def convert_image(
    source: Path,
    destination: Path,
    quality: int,
    method: int,
    force: bool,
) -> tuple[int, int]:
    same_file = source.resolve() == destination.resolve()
    if destination.exists() and not force and not same_file:
        raise FileExistsError(
            f"output already exists: {destination}; pass --force to replace it"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    source_size = source.stat().st_size

    with Image.open(source) as image:
        if getattr(image, "n_frames", 1) > 1:
            print(
                f"WARNING: {source} is animated; only the first frame is converted",
                file=sys.stderr,
            )
            image.seek(0)
        oriented = ImageOps.exif_transpose(image)
        has_alpha = oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info
        converted = oriented.convert("RGBA" if has_alpha else "RGB")
        converted.load()

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.stem}-",
            suffix=".webp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        converted.save(
            temporary_path,
            "WEBP",
            quality=quality,
            method=method,
            alpha_quality=100,
        )
        temporary_path.replace(destination)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    return source_size, destination.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Image files or directories")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory that will receive .webp files",
    )
    parser.add_argument(
        "--quality",
        type=bounded_integer(1, 100),
        default=82,
        help="WebP quality from 1 to 100 (default: 82)",
    )
    parser.add_argument(
        "--method",
        type=bounded_integer(0, 6),
        default=6,
        help="WebP compression method from 0 to 6 (default: 6)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search input directories recursively",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing output files",
    )
    args = parser.parse_args()

    try:
        sources = collect_sources(args.inputs, args.recursive)
    except ValueError as exc:
        parser.error(str(exc))

    destinations: dict[Path, Path] = {}
    for source in sources:
        destination = args.output_dir / f"{source.stem}.webp"
        previous = destinations.get(destination)
        if previous and previous.resolve() != source.resolve():
            parser.error(
                f"output name collision: {previous} and {source} both map to {destination}"
            )
        destinations[destination] = source

    failures = 0
    original_total = 0
    webp_total = 0
    for destination, source in destinations.items():
        try:
            original_size, webp_size = convert_image(
                source,
                destination,
                args.quality,
                args.method,
                args.force,
            )
        except Exception as exc:
            failures += 1
            print(f"ERROR: {source}: {exc}", file=sys.stderr)
            continue
        original_total += original_size
        webp_total += webp_size
        change = (
            (1 - webp_size / original_size) * 100 if original_size else 0
        )
        print(
            f"{source.name} -> {destination.name}: "
            f"{original_size:,} -> {webp_size:,} bytes ({change:.1f}% smaller)"
        )

    if failures:
        print(f"FAILED: {failures} image(s) could not be converted", file=sys.stderr)
        return 1

    total_change = (
        (1 - webp_total / original_total) * 100 if original_total else 0
    )
    print(
        f"OK: {len(destinations)} image(s), "
        f"{original_total:,} -> {webp_total:,} bytes "
        f"({total_change:.1f}% smaller)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
