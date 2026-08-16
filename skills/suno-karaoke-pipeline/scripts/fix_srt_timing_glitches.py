#!/usr/bin/env python3
"""Fix common SRT timing glitches that come out of ASR tools (whisper etc.)
and that cause players like VLC to freeze a subtitle on screen or flash two
lines at once:

  - overlapping cues (cue N ends after cue N+1 starts)
  - zero or negative duration cues
  - cues shorter than a minimum duration (the "frozen subtitle" symptom is
    usually actually the *opposite*: a cue so short the player keeps
    showing it because the next one hasn't started yet -- padding it out
    and enforcing a gap fixes both)
  - cues with no gap at all between them (some players merge/flicker)

Usage:
    python fix_srt_timing_glitches.py input.srt -o fixed.srt
    python fix_srt_timing_glitches.py input.srt -o fixed.srt --min-duration 0.8 --min-gap 0.08
"""
import argparse
import re
import sys

TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})")
BLOCK_RE = re.compile(
    r"\d+\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n(.*?)(?=\n\n|\Z)",
    re.S,
)


def parse_time(s):
    m = TIME_RE.match(s)
    h, mi, sec, ms = (int(x) for x in m.groups())
    return ((h * 60 + mi) * 60 + sec) * 1000 + ms


def format_time(ms):
    if ms < 0:
        ms = 0
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for match in BLOCK_RE.finditer(text.strip() + "\n\n"):
        start, end, body = match.groups()
        cues.append({"start": parse_time(start), "end": parse_time(end), "text": body.strip()})
    return cues


def fix_cues(cues, min_duration_ms, min_gap_ms):
    fixed = 0
    cues = sorted(cues, key=lambda c: c["start"])
    for i, cue in enumerate(cues):
        if cue["end"] <= cue["start"]:
            cue["end"] = cue["start"] + min_duration_ms
            fixed += 1
        elif cue["end"] - cue["start"] < min_duration_ms:
            cue["end"] = cue["start"] + min_duration_ms
            fixed += 1

        if i + 1 < len(cues):
            next_start = cues[i + 1]["start"]
            latest_allowed_end = next_start - min_gap_ms
            if cue["end"] > latest_allowed_end:
                cue["end"] = max(cue["start"] + 1, latest_allowed_end)
                fixed += 1
    return cues, fixed


def render(cues):
    lines = []
    for i, cue in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{format_time(cue['start'])} --> {format_time(cue['end'])}")
        lines.append(cue["text"])
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input .srt file")
    ap.add_argument("-o", "--output", required=True, help="output .srt path")
    ap.add_argument("--min-duration", type=float, default=0.6, help="minimum cue duration in seconds (default 0.6)")
    ap.add_argument("--min-gap", type=float, default=0.05, help="minimum gap between consecutive cues in seconds (default 0.05)")
    ap.add_argument("--encoding", default="utf-8", help="input encoding; try cp949 or shift-jis if you get garbled text")
    args = ap.parse_args()

    with open(args.input, "r", encoding=args.encoding, errors="replace") as f:
        text = f.read()

    cues = parse_srt(text)
    if not cues:
        sys.exit("No cues parsed -- is this a valid SRT file? (try --encoding if the text looks garbled)")

    fixed_cues, num_fixed = fix_cues(cues, int(args.min_duration * 1000), int(args.min_gap * 1000))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(render(fixed_cues))

    print(f"{len(cues)} cues processed, {num_fixed} timing adjustments made -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
