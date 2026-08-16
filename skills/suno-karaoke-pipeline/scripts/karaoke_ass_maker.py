#!/usr/bin/env python3
"""Turn a line-timed SRT (lyrics) into an .ass karaoke subtitle, with each
line's duration split across its characters proportionally so the
word-by-word highlight sweeps at a roughly natural pace. This is an
approximation -- if you have real word-level timestamps, edit the \\k
values by hand afterwards -- but it looks good for most song lyrics
without needing forced alignment.

Usage:
    python karaoke_ass_maker.py lyrics.srt -o lyrics.ass
    python karaoke_ass_maker.py lyrics.srt -o lyrics.ass --font "Noto Sans CJK JP" --highlight-color "&H0000FFFF"

Run fix_srt_timing_glitches.py on the SRT first -- overlapping or
zero-duration cues make the karaoke sweep look broken.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_srt_timing_glitches import parse_srt  # noqa: E402

ASS_HEADER_TEMPLATE = """[Script Info]
Title: {title}
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font},{font_size},{base_color},{highlight_color},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,20,20,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def fmt_ass_time(ms):
    cs = round(ms / 10)  # centiseconds
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def line_to_karaoke_text(text, duration_ms):
    """Split `text` into per-character \\k tags proportional to length."""
    chars = [c for c in text if c.strip() != ""]
    if not chars:
        return text
    per_char_cs = max(1, round((duration_ms / 100) / len(text)))
    out = []
    for ch in text:
        if ch == " ":
            out.append(" ")
        else:
            out.append(f"{{\\k{per_char_cs}}}{ch}")
    return "".join(out)


def build_ass(cues, title, font, font_size, base_color, highlight_color, res_x, res_y):
    header = ASS_HEADER_TEMPLATE.format(
        title=title, font=font, font_size=font_size,
        base_color=base_color, highlight_color=highlight_color,
        res_x=res_x, res_y=res_y,
    )
    lines = [header]
    for cue in cues:
        start = fmt_ass_time(cue["start"])
        end = fmt_ass_time(cue["end"])
        text = cue["text"].replace("\n", "\\N")
        karaoke_text = line_to_karaoke_text(text, cue["end"] - cue["start"])
        lines.append(f"Dialogue: 0,{start},{end},Karaoke,,0,0,0,,{karaoke_text}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input .srt file with line-level lyric timing")
    ap.add_argument("-o", "--output", required=True, help="output .ass path")
    ap.add_argument("--title", default=None, help="song title for the ASS header (default: input filename)")
    ap.add_argument("--font", default="Noto Sans CJK KR", help="font name (must be installed where the video is rendered)")
    ap.add_argument("--font-size", type=int, default=64)
    ap.add_argument("--base-color", default="&H00FFFFFF", help="ASS BGR color for un-sung text (default white)")
    ap.add_argument("--highlight-color", default="&H0000D7FF", help="ASS BGR color for the karaoke sweep (default gold)")
    ap.add_argument("--resolution", default="1920x1080", help="PlayResX x PlayResY, should match the final video, e.g. 1080x1920 for vertical")
    ap.add_argument("--encoding", default="utf-8", help="input SRT encoding; try cp949 or shift-jis if the text looks garbled")
    args = ap.parse_args()

    res_x, res_y = (int(v) for v in args.resolution.lower().split("x"))

    for enc in [args.encoding, "utf-8", "cp949", "shift-jis"]:
        try:
            with open(args.input, "r", encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        sys.exit(f"Could not decode {args.input} with any known encoding")

    cues = parse_srt(text)
    if not cues:
        sys.exit(f"No cues parsed from {args.input}")

    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    ass_text = build_ass(cues, title, args.font, args.font_size, args.base_color, args.highlight_color, res_x, res_y)

    with open(args.output, "w", encoding="utf-8-sig") as f:
        f.write(ass_text)

    print(f"Wrote {len(cues)} karaoke lines -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
