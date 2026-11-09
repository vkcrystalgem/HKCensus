"""Validate and package the prepared Google Play en-US listing.

Requires Python 3.10+ and Pillow. Never uploads or publishes anything.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageCms


ROOT = Path(__file__).resolve().parent
ZIP_NAME = "HKCensus-GooglePlay-en-US.zip"
MIB = 1024 * 1024
TEXT_FIELDS = (
    ("appName", "en-US/app-name.txt", 30, True),
    ("shortDescription", "en-US/short-description.txt", 80, True),
    ("fullDescription", "en-US/full-description.txt", 4000, False),
)
SCREENSHOT_GROUPS = (
    ("phoneScreenshots", "phone", 1080, 3840),
    ("sevenInchScreenshots", "tablet-7inch", 320, 3840),
    ("tenInchScreenshots", "tablet-10inch", 1080, 7680),
)


class ValidationError(ValueError):
    pass


def file_record(path: Path, play_field: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "playField": play_field,
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def validate_png(path: Path, mode: str, max_bytes: int) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"Missing image: {path.relative_to(ROOT).as_posix()}")
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise ValidationError(f"{path.name}: {len(data):,} bytes exceeds {max_bytes:,}.")
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError(f"{path.name}: expected a genuine PNG file.")
    expected_color_type = {"RGB": 2, "RGBA": 6}[mode]
    if data[24] != 8 or data[25] != expected_color_type:
        raise ValidationError(f"{path.name}: expected an 8-bit/channel {mode} PNG (not palette or grayscale).")
    try:
        with Image.open(io.BytesIO(data)) as check:
            check.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.format != "PNG" or image.mode != mode:
                raise ValidationError(f"{path.name}: expected PNG mode {mode}, found {image.mode}.")
            if "transparency" in image.info:
                raise ValidationError(f"{path.name}: PNG colour-key transparency is not permitted.")
            if mode == "RGBA" and image.getchannel("A").getextrema() != (255, 255):
                raise ValidationError(f"{path.name}: the store icon must be fully opaque (all alpha values 255).")
            profile = image.info.get("icc_profile")
            profile_description = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(profile))).strip() if profile else None
            return {
                "width": image.width,
                "height": image.height,
                "format": "PNG",
                "mode": image.mode,
                "bitsPerPixel": 32 if mode == "RGBA" else 24,
                "opaque": True,
                "embeddedIccProfile": bool(profile),
                "iccProfileDescription": profile_description,
            }
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(f"{path.name}: invalid or unreadable PNG ({type(exc).__name__}).") from exc


def collect_packet(include_sources: bool = False) -> tuple[dict[str, Any], dict[str, bytes]]:
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    counts: dict[str, Any] = {"textCharacters": {}, "screenshots": {}}

    def add(path: Path, field: str, extra: dict[str, Any] | None = None):
        record = file_record(path, field)
        record.update(extra or {})
        records.append(record)
        payloads[record["path"]] = path.read_bytes()

    for field, relative, limit, single_line in TEXT_FIELDS:
        path = ROOT / relative
        try:
            if not path.is_file():
                raise ValidationError(f"Missing text field: {relative}")
            value = path.read_text(encoding="utf-8-sig").strip()
            if not value:
                raise ValidationError(f"{relative}: text must not be empty.")
            if len(value) > limit:
                raise ValidationError(f"{relative}: {len(value)} characters exceeds the {limit}-character limit.")
            if single_line and ("\n" in value or "\r" in value):
                raise ValidationError(f"{relative}: this field must be a single line.")
            counts["textCharacters"][field] = {"characters": len(value), "limit": limit}
            add(path, field, {"characters": len(value), "characterLimit": limit})
        except (ValidationError, UnicodeError, OSError) as exc:
            errors.append(str(exc))

    for field, relative, dimensions, mode, byte_limit in (
        ("appIcon", "graphics/app-icon-512.png", (512, 512), "RGBA", MIB),
        ("featureGraphic", "graphics/feature-graphic-1024x500.png", (1024, 500), "RGB", 15 * MIB),
    ):
        path = ROOT / relative
        try:
            details = validate_png(path, mode, byte_limit)
            if (details["width"], details["height"]) != dimensions:
                raise ValidationError(f"{relative}: expected {dimensions[0]} x {dimensions[1]} pixels.")
            if not details["embeddedIccProfile"] or "srgb" not in details["iccProfileDescription"].lower():
                raise ValidationError(f"{relative}: expected an embedded sRGB colour profile.")
            add(path, field, details)
        except (ValidationError, OSError) as exc:
            errors.append(str(exc))

    for field, folder, minimum, maximum in SCREENSHOT_GROUPS:
        directory = ROOT / "screenshots" / folder
        images = sorted(directory.glob("*.png")) if directory.is_dir() else []
        unsupported = sorted(p.name for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".webp", ".gif"}) if directory.is_dir() else []
        if unsupported:
            errors.append(f"screenshots/{folder}: this packet requires RGB PNG screenshots; unsupported files: {', '.join(unsupported)}.")
        counts["screenshots"][folder] = len(images)
        if not 4 <= len(images) <= 8:
            errors.append(f"screenshots/{folder}: requires 4-8 genuine captures; found {len(images)}. Complete capture collection before packaging.")
        for position, path in enumerate(images, 1):
            try:
                details = validate_png(path, "RGB", 8 * MIB)
                width, height = details["width"], details["height"]
                if not (minimum <= width <= maximum and minimum <= height <= maximum):
                    raise ValidationError(f"{path.relative_to(ROOT).as_posix()}: each side must be {minimum}-{maximum} pixels; found {width} x {height}.")
                if width * 16 != height * 9:
                    raise ValidationError(f"{path.relative_to(ROOT).as_posix()}: expected native portrait 9:16 proportions, found {width} x {height}.")
                add(path, field, {**details, "displayOrder": position, "deviceGroup": folder})
            except (ValidationError, OSError) as exc:
                errors.append(str(exc))

    for relative in ("README.md", "en-US/UPLOAD_GUIDE.md", "en-US/alt-text-suggestions.md"):
        path = ROOT / relative
        if not path.is_file() or not path.stat().st_size:
            errors.append(f"Missing packet documentation: {relative}")
        else:
            add(path, "uploadInstructions")

    if include_sources:
        path = ROOT / "ASSET_SOURCES.md"
        if not path.is_file():
            errors.append("--include-sources requested but ASSET_SOURCES.md is missing.")
        else:
            add(path, "assetAttribution")

    provenance_path = ROOT / "provenance.json"
    provenance = None
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8-sig"))
            if not isinstance(provenance, dict):
                raise ValidationError("provenance.json must contain a JSON object.")
        except (ValueError, OSError) as exc:
            errors.append(f"Cannot read capture provenance: {exc}")
    if errors:
        raise ValidationError("Listing packet validation failed:\n" + "\n".join(f"- {error}" for error in errors))

    manifest = {
        "schemaVersion": 1,
        "locale": "en-US",
        "packageName": "com.vkcrystalgem.hkcensus",
        "status": "prepared-for-manual-upload",
        "publishedByThisScript": False,
        "counts": counts,
        "files": sorted(records, key=lambda item: item["path"]),
        "captureProvenance": provenance,
        "provenanceNote": "Capture origin must be verified against the installed review APK; image dimensions alone do not prove authenticity.",
        "omittedFields": ["previewVideo", "desktopScreenshots", "androidXrAssets"],
    }
    return manifest, payloads


def export_capture(raw_path: str | Path, final_path: str | Path, overwrite: bool = False) -> dict[str, Any]:
    """Losslessly export an emulator PNG as RGB, retaining every decoded RGB pixel.

    No resizing, cropping, drawing, compositing, or colour conversion is performed.
    Only an already-opaque RGB/RGBA PNG is accepted. Raw capture stays untouched.
    """
    raw_path, final_path = Path(raw_path), Path(final_path)
    if raw_path.resolve() == final_path.resolve():
        raise ValidationError("Raw capture and export must be different files; preserve the original capture.")
    if final_path.suffix.lower() != ".png":
        raise ValidationError("Screenshot export destination must end in .png.")
    if final_path.exists() and not overwrite:
        raise ValidationError(f"Export already exists: {final_path}. Pass overwrite=True or --overwrite to replace it explicitly.")
    with Image.open(raw_path) as raw:
        raw.load()
        if raw.format != "PNG" or raw.mode not in {"RGB", "RGBA"}:
            raise ValidationError("Raw capture must be an RGB or RGBA PNG.")
        if "transparency" in raw.info:
            raise ValidationError("Capture has colour-key transparency; cannot export it as an opaque screenshot.")
        if raw.mode == "RGBA" and raw.getchannel("A").getextrema() != (255, 255):
            raise ValidationError("Capture contains transparency; cannot remove alpha losslessly.")
        original_rgb = raw.convert("RGB")
        output = original_rgb.copy()
        metadata = {"icc_profile": raw.info["icc_profile"]} if raw.info.get("icc_profile") else {}
        buffer = io.BytesIO()
        output.save(buffer, format="PNG", optimize=True, **metadata)
        exported_bytes = buffer.getvalue()
        with Image.open(io.BytesIO(exported_bytes)) as check:
            check.load()
            if check.mode != "RGB" or check.size != raw.size or ImageChops.difference(check, original_rgb).getbbox():
                raise ValidationError("Export pixel verification failed; destination was not written.")
        result = {
            "rawFile": str(raw_path), "exportedFile": str(final_path),
            "rawSha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            "exportedSha256": hashlib.sha256(exported_bytes).hexdigest(),
            "width": raw.width, "height": raw.height,
            "rawMode": raw.mode, "exportedMode": "RGB",
            "rgbPixelsIdentical": True,
            "operation": "drop-fully-opaque-alpha" if raw.mode == "RGBA" else "lossless-RGB-PNG-encode",
        }
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(exported_bytes)
    return result


def package_listing(check_only: bool = False, include_sources: bool = False, output: Path | None = None) -> dict[str, Any]:
    manifest, payloads = collect_packet(include_sources)
    if check_only:
        return {"valid": True, "counts": manifest["counts"], "files": len(payloads), "provenancePresent": manifest["captureProvenance"] is not None}
    output = (output or ROOT / ZIP_NAME).resolve()
    if output.suffix.lower() != ".zip":
        raise ValidationError("Packet output must be a .zip file.")
    if output in {(ROOT / path).resolve() for path in payloads}:
        raise ValidationError("ZIP output cannot overwrite an input asset.")
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    payloads["manifest.json"] = manifest_bytes
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(payloads.items()):
                entry = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise ValidationError(f"ZIP integrity check failed: {corrupt}")
        os.replace(temporary, output)
        (ROOT / "manifest.json").write_bytes(manifest_bytes)
    finally:
        if temporary.is_file():
            temporary.unlink()
    return {"valid": True, "zip": str(output), "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "counts": manifest["counts"], "files": len(payloads)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate without writing a manifest or ZIP.")
    parser.add_argument("--include-sources", action="store_true", help="Include ASSET_SOURCES.md as optional attribution documentation.")
    parser.add_argument("--output", type=Path, help=f"ZIP path; default: store-listing/{ZIP_NAME}")
    parser.add_argument("--export-capture", nargs=2, metavar=("RAW_PNG", "FINAL_PNG"), help="Losslessly export one opaque emulator PNG as a 24-bit RGB PNG; does not build the packet.")
    parser.add_argument("--overwrite", action="store_true", help="Permit replacing the explicit --export-capture destination.")
    args = parser.parse_args()
    try:
        if args.export_capture:
            if args.check_only or args.include_sources or args.output:
                raise ValidationError("--export-capture must be used separately from packet options.")
            result = export_capture(*args.export_capture, overwrite=args.overwrite)
        else:
            if args.overwrite:
                raise ValidationError("--overwrite applies only to --export-capture.")
            result = package_listing(args.check_only, args.include_sources, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValidationError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
