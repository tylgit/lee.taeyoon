#!/usr/bin/env python3
"""Transcribe Japanese audio/video into an SRT file, keeping kanji (not
romanized) text -- a thin wrapper around the `whisper` CLI that forces
language=Japanese and normalizes the output filename/location.

Requires openai-whisper to be installed and on PATH:
    pip install openai-whisper
(or faster-whisper's CLI equivalent -- pass --engine faster-whisper if you
have `faster-whisper` installed instead; it's much quicker on CPU.)

Usage:
    python kanji_srt_maker.py song.mp3 -o song.srt
    python kanji_srt_maker.py song.mp3 --model medium -o song.srt
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def run_whisper(audio_path, model, work_dir):
    if shutil.which("whisper") is None:
        sys.exit("`whisper` not found on PATH. Install with: pip install openai-whisper")
    cmd = [
        "whisper", audio_path,
        "--language", "Japanese",
        "--task", "transcribe",
        "--model", model,
        "--output_format", "srt",
        "--output_dir", work_dir,
    ]
    print("Running:", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    return os.path.join(work_dir, stem + ".srt")


def run_faster_whisper(audio_path, model, work_dir):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper not installed. Install with: pip install faster-whisper")

    wm = WhisperModel(model)
    segments, _ = wm.transcribe(audio_path, language="ja")

    def fmt_ts(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        ms = int((s - int(s)) * 1000)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"

    stem = os.path.splitext(os.path.basename(audio_path))[0]
    out_path = os.path.join(work_dir, stem + ".srt")
    with open(out_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{seg.text.strip()}\n\n")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="input audio or video file")
    ap.add_argument("-o", "--output", required=True, help="output .srt path")
    ap.add_argument("--model", default="medium", help="whisper model size (tiny/base/small/medium/large), default medium")
    ap.add_argument("--engine", choices=["whisper", "faster-whisper"], default="whisper")
    args = ap.parse_args()

    if not os.path.exists(args.audio):
        sys.exit(f"Input file not found: {args.audio}")

    with tempfile.TemporaryDirectory() as work_dir:
        if args.engine == "whisper":
            raw_srt = run_whisper(args.audio, args.model, work_dir)
        else:
            raw_srt = run_faster_whisper(args.audio, args.model, work_dir)

        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        shutil.move(raw_srt, args.output)

    print(f"Wrote {args.output}", file=sys.stderr)
    print("Tip: run fix_srt_timing_glitches.py on this file before using it for karaoke -- "
          "whisper segment timings sometimes overlap or freeze on silence.", file=sys.stderr)


if __name__ == "__main__":
    main()
