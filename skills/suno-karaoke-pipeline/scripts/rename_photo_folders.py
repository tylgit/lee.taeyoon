#!/usr/bin/env python3
"""Rename photo folders to a "YYYY-MM-DD original name" prefix, using the
EXIF capture date of the photos inside (falls back to file mtime when a
photo has no EXIF date, e.g. screenshots or edited exports).

Usage:
    python rename_photo_folders.py /path/to/photo/library --dry-run
    python rename_photo_folders.py /path/to/photo/library

Only immediate subfolders of the given root that contain at least one image
are considered -- the root itself is never renamed. Folders that already
start with a YYYY-MM-DD prefix are left alone (safe to re-run).

Needs Pillow for real EXIF reading (pip install Pillow). Without it, the
script still runs but uses file modification time for every folder, which
prints a warning so you know the dates may be less accurate.
"""
import argparse
import datetime
import os
import re
import sys

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".raw", ".cr2", ".nef", ".dng"}
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ _-]")

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def exif_date(path):
    if not HAVE_PIL:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            for tag_id, value in exif.items():
                if TAGS.get(tag_id) in ("DateTimeOriginal", "DateTime"):
                    return datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S").date()
    except Exception:
        return None
    return None


def folder_date(folder):
    """Earliest date found among photos in the folder (EXIF, else mtime)."""
    best = None
    used_fallback = False
    for name in os.listdir(folder):
        ext = os.path.splitext(name)[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        full = os.path.join(folder, name)
        d = exif_date(full)
        if d is None:
            used_fallback = True
            d = datetime.date.fromtimestamp(os.path.getmtime(full))
        if best is None or d < best:
            best = d
    return best, used_fallback


def sanitize(name):
    return re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="folder containing photo subfolders to rename")
    ap.add_argument("--dry-run", action="store_true", help="print planned renames without touching anything")
    args = ap.parse_args()

    if not HAVE_PIL:
        print("WARNING: Pillow not installed -- using file mtime for all folders (pip install Pillow for accurate EXIF dates)", file=sys.stderr)

    if not os.path.isdir(args.root):
        print(f"Not a directory: {args.root}", file=sys.stderr)
        sys.exit(1)

    renamed, skipped = 0, 0
    for name in sorted(os.listdir(args.root)):
        full = os.path.join(args.root, name)
        if not os.path.isdir(full):
            continue
        if DATE_PREFIX_RE.match(name):
            skipped += 1
            continue

        date, used_fallback = folder_date(full)
        if date is None:
            print(f"SKIP (no photos found): {name}", file=sys.stderr)
            skipped += 1
            continue

        new_name = sanitize(f"{date.isoformat()} {name}")
        new_full = os.path.join(args.root, new_name)
        note = " (mtime fallback)" if used_fallback else ""
        print(f"{name}  ->  {new_name}{note}")

        if not args.dry_run:
            if os.path.exists(new_full):
                print(f"  SKIPPED: target already exists: {new_full}", file=sys.stderr)
                skipped += 1
                continue
            os.rename(full, new_full)
        renamed += 1

    verb = "Would rename" if args.dry_run else "Renamed"
    print(f"\n{verb} {renamed} folder(s), skipped {skipped}", file=sys.stderr)


if __name__ == "__main__":
    main()
