#!/usr/bin/env python3
"""Combine an audio track and a subtitle file (.ass karaoke or plain .srt)
into an MP4 lyric video, with a solid color, gradient, or still-image
background. Requires ffmpeg (and ffprobe) on PATH.

Usage:
    python make_video.py song.mp3 song.ass -o song.mp4
    python make_video.py song.mp3 song.srt -o song.mp4 --background "gradient:1a1a2e:16213e"
    python make_video.py song.mp3 song.ass -o song.mp4 --background cover.jpg --resolution 1080x1920

IMPORTANT -- avoiding the "double subtitles in VLC" problem:
    Subtitles here are always burned into the video frame (hard-subbed via
    ffmpeg's ass/subtitles filter). Do NOT also mux the .ass/.srt file into
    the mp4 as a soft subtitle track (e.g. with `-c:s mov_text`) and do NOT
    load the .ass file again in VLC "Open with subtitle file" -- that's
    what causes two overlapping copies of the lyrics on screen. Pick one:
    burned-in (what this script does, works everywhere, can't be toggled
    off) or soft subtitle track (togglable, but you own that copy
    separately) -- never both.
"""
import argparse
import os
import shutil
import subprocess
import sys


def require(binary):
    if shutil.which(binary) is None:
        sys.exit(f"`{binary}` not found on PATH. Install ffmpeg (which provides both ffmpeg and ffprobe).")


def get_audio_duration(audio_path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
    ])
    return float(out.strip())


def escape_for_filter(path):
    # ffmpeg filtergraph args need ':' and '\' and single quotes escaped.
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_background_input(background, duration, resolution):
    """Return (ffmpeg -i args, video filter source label) for the background."""
    if background.startswith("gradient:"):
        _, c1, c2 = background.split(":")
        vf = (
            f"gradients=s={resolution}:d={duration}:c0=0x{c1}:c1=0x{c2}"
        )
        return ["-f", "lavfi", "-i", vf], None
    if os.path.isfile(background):
        return ["-loop", "1", "-i", background], None
    # Treat as a plain color name/hex.
    return ["-f", "lavfi", "-i", f"color=c={background}:s={resolution}:d={duration}"], None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="input audio file (mp3/wav/...)")
    ap.add_argument("subtitle", help="input .ass (karaoke) or .srt subtitle file")
    ap.add_argument("-o", "--output", required=True, help="output .mp4 path")
    ap.add_argument("--background", default="black",
                     help="color name/hex (e.g. '#101020'), 'gradient:COLOR1:COLOR2' (hex, no #), "
                          "or a path to a still image. Default: black")
    ap.add_argument("--resolution", default="1920x1080", help="output resolution, e.g. 1080x1920 for vertical/Shorts")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    require("ffmpeg")
    require("ffprobe")

    if not os.path.exists(args.audio):
        sys.exit(f"Audio file not found: {args.audio}")
    if not os.path.exists(args.subtitle):
        sys.exit(f"Subtitle file not found: {args.subtitle}")

    duration = get_audio_duration(args.audio)
    bg_input_args, _ = build_background_input(args.background, duration, args.resolution)

    is_image = os.path.isfile(args.background)
    sub_ext = os.path.splitext(args.subtitle)[1].lower()
    sub_filter = "ass" if sub_ext == ".ass" else "subtitles"
    vf = f"{sub_filter}={escape_for_filter(args.subtitle)}"
    if is_image:
        w, h = args.resolution.split("x")
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}," + vf

    cmd = [
        "ffmpeg", "-y",
        *bg_input_args,
        "-i", args.audio,
        "-vf", vf,
        "-r", str(args.fps),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        args.output,
    ]

    print("Running:", " ".join(cmd), file=sys.stderr)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)

    print(f"Wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
