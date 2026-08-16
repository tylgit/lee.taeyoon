#!/usr/bin/env python3
"""Batch-run make_video.py over every audio file in a folder, pairing each
one with a same-basename subtitle file (.ass preferred, falling back to
.srt) found in the same folder.

Usage:
    python batch_video.py songs/ --out-dir videos/
    python batch_video.py songs/ --out-dir videos/ --background "gradient:1a1a2e:16213e" --resolution 1080x1920
"""
import argparse
import glob
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAKE_VIDEO = os.path.join(SCRIPT_DIR, "make_video.py")


def find_subtitle(input_dir, stem):
    for ext in (".ass", ".srt"):
        candidate = os.path.join(input_dir, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", help="folder containing audio files and matching subtitle files")
    ap.add_argument("--out-dir", required=True, help="where to write .mp4 files")
    ap.add_argument("--audio-ext", default=".mp3")
    ap.add_argument("--background", default="black")
    ap.add_argument("--resolution", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        sys.exit(f"Folder not found: {args.input_dir}")
    os.makedirs(args.out_dir, exist_ok=True)

    audio_files = sorted(glob.glob(os.path.join(args.input_dir, "*" + args.audio_ext)))
    if not audio_files:
        sys.exit(f"No *{args.audio_ext} files found in {args.input_dir}")

    ok, failed, skipped = 0, [], []
    for audio_path in audio_files:
        stem = os.path.splitext(os.path.basename(audio_path))[0]
        subtitle_path = find_subtitle(args.input_dir, stem)
        if subtitle_path is None:
            print(f"SKIP (no .ass/.srt found): {stem}", file=sys.stderr)
            skipped.append(stem)
            continue

        out_path = os.path.join(args.out_dir, stem + ".mp4")
        cmd = [
            sys.executable, MAKE_VIDEO, audio_path, subtitle_path,
            "-o", out_path,
            "--background", args.background,
            "--resolution", args.resolution,
            "--fps", str(args.fps),
        ]
        print(f"--- {stem} ---", file=sys.stderr)
        result = subprocess.run(cmd)
        if result.returncode == 0:
            ok += 1
        else:
            failed.append(stem)

    print(f"\n{ok} videos made, {len(failed)} failed, {len(skipped)} skipped (no subtitle)", file=sys.stderr)
    if failed:
        print("Failed:", ", ".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
