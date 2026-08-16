#!/usr/bin/env python3
"""Batch-run karaoke_ass_maker.py over every lyric file in a folder,
pairing each one with its same-basename audio file.

Usage:
    python batch_karaoke.py songs/
    python batch_karaoke.py songs/ --pattern "*.srt" --audio-ext .mp3 --out-dir ass/

For every "<name>.srt" this looks for "<name>.mp3" (or whatever
--audio-ext is) in the same folder. If the audio is missing, the lyric
file is still converted -- audio is only used to sanity-check that a
matching song exists, make_video.py needs it later, not this step.

Handles two problems that come up constantly with lyric files exported
from different tools: files that got moved into a folder that doesn't
actually exist yet (the --out-dir is created up front), and files saved
in cp949/shift-jis instead of utf-8 (each file is tried against a list of
encodings before giving up).
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import karaoke_ass_maker  # noqa: E402
from fix_srt_timing_glitches import parse_srt  # noqa: E402

ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "cp949", "shift-jis"]


def read_with_fallback_encoding(path):
    last_err = None
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read(), enc
        except (UnicodeDecodeError, LookupError) as e:
            last_err = e
    raise last_err


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", help="folder containing lyric files")
    ap.add_argument("--pattern", default="*.srt", help="glob pattern for lyric files (default *.srt)")
    ap.add_argument("--audio-ext", default=".mp3", help="expected audio extension to pair against, for the warning check (default .mp3)")
    ap.add_argument("--out-dir", default=None, help="where to write .ass files (default: same folder as the input)")
    ap.add_argument("--font", default="Noto Sans CJK KR")
    ap.add_argument("--resolution", default="1920x1080")
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        sys.exit(f"Folder not found: {args.input_dir}")

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    lyric_files = sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))
    if not lyric_files:
        sys.exit(f"No files matching {args.pattern} found in {args.input_dir}")

    ok, failed = 0, []
    for path in lyric_files:
        stem = os.path.splitext(os.path.basename(path))[0]
        audio_path = os.path.join(args.input_dir, stem + args.audio_ext)
        if not os.path.exists(audio_path):
            print(f"WARNING: no matching audio for {os.path.basename(path)} (looked for {os.path.basename(audio_path)})", file=sys.stderr)

        out_dir = args.out_dir or args.input_dir
        out_path = os.path.join(out_dir, stem + ".ass")

        try:
            text, enc = read_with_fallback_encoding(path)
            cues = parse_srt(text)
            if not cues:
                raise ValueError("no cues parsed")
            ass_text = karaoke_ass_maker.build_ass(
                cues, title=stem, font=args.font, font_size=64,
                base_color="&H00FFFFFF", highlight_color="&H0000D7FF",
                res_x=int(args.resolution.split("x")[0]), res_y=int(args.resolution.split("x")[1]),
            )
            with open(out_path, "w", encoding="utf-8-sig") as f:
                f.write(ass_text)
            print(f"OK ({enc}): {path} -> {out_path}")
            ok += 1
        except Exception as e:
            print(f"FAILED: {path} ({e})", file=sys.stderr)
            failed.append(path)

    print(f"\n{ok} converted, {len(failed)} failed", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
