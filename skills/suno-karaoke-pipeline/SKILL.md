---
name: suno-karaoke-pipeline
description: End-to-end pipeline for turning Suno.ai song links into finished Korean/Japanese karaoke lyric videos (MP4) -- resolving and deduping share links, downloading songs from Suno, transcribing Japanese lyrics to kanji SRT, fixing SRT timing glitches, building word-highlight ASS karaoke subtitles, and rendering the final video with ffmpeg, individually or in batch. Also includes a standalone photo-folder-by-date renamer. Use this skill whenever the user mentions Suno links/downloads, making a karaoke or lyrics video, fixing broken/frozen SRT subtitles, double subtitles in VLC, ASS karaoke files, or batch-renaming photo folders by date -- even if they only name one step of the pipeline, since the other scripts here are usually what they need next.
---

# Suno → Karaoke Video Pipeline

A 10-script pipeline, built and hardened over repeated real runs, that goes from a
list of Suno song links to finished MP4 karaoke lyric videos. Every script is a
standalone CLI in `scripts/` -- run any one on its own, or chain them as a pipeline.
Nothing here needs to be imported as a library except `batch_karaoke.py`, which
reuses `karaoke_ass_maker.py` directly to avoid re-parsing SRT twice.

## Pipeline overview

```
links.txt
   │  resolve_links.py     (expand short/redirect links to final Suno URLs)
   ▼
resolved.txt
   │  dedupe_links.py      (drop duplicate links, ignoring tracking params)
   ▼
deduped.txt
   │  suno_downloader.py   (download .mp3 + lyrics + metadata per song)
   ▼
downloads/*.mp3, *.txt, *.json
   │  kanji_srt_maker.py   (only if you need ASR transcription, e.g. no lyrics
   │                        came back from Suno, or you want synced timing --
   │                        skip this if you already have a hand-timed .srt)
   ▼
*.srt (line-level lyric timing)
   │  fix_srt_timing_glitches.py   (ALWAYS run this before karaoke_ass_maker)
   ▼
*.srt (clean timing)
   │  karaoke_ass_maker.py  (or batch_karaoke.py for a whole folder)
   ▼
*.ass (word-highlight karaoke subtitles)
   │  make_video.py         (or batch_video.py for a whole folder)
   ▼
*.mp4 (finished karaoke video)
```

Photo folder renaming (`rename_photo_folders.py`) is unrelated to the song
pipeline -- it's a separate utility for organizing a photo library by capture
date, bundled here because it was built in the same session.

## Scripts

| Script | Purpose | Key flags |
|---|---|---|
| `resolve_links.py` | Follow redirects on a list of URLs | `-o`, `--timeout` |
| `dedupe_links.py` | Remove duplicate URLs (normalizes tracking params, http/https, www) | `-o` |
| `suno_downloader.py` | Download audio + lyrics + metadata from Suno links | `--out-dir` (required), `--token` |
| `rename_photo_folders.py` | Rename photo subfolders to `YYYY-MM-DD original name` using EXIF date | `--dry-run` |
| `kanji_srt_maker.py` | Whisper-transcribe Japanese audio to a kanji `.srt` | `-o` (required), `--model`, `--engine` |
| `fix_srt_timing_glitches.py` | Fix overlapping/zero-duration/too-short SRT cues | `-o` (required), `--min-duration`, `--min-gap`, `--encoding` |
| `karaoke_ass_maker.py` | Convert a line-timed `.srt` into a word-highlight `.ass` | `-o` (required), `--font`, `--highlight-color`, `--resolution` |
| `batch_karaoke.py` | Run `karaoke_ass_maker` over every `.srt` in a folder | `--pattern`, `--out-dir` |
| `make_video.py` | Render audio + subtitle + background into an `.mp4` via ffmpeg | `-o` (required), `--background`, `--resolution` |
| `batch_video.py` | Run `make_video` over every audio file in a folder | `--out-dir` (required), `--background` |

Run any script with `--help` for the full flag list and examples -- each one has
a detailed docstring at the top.

## Getting a Suno token

`suno_downloader.py` only needs a token for songs that aren't public:

1. Log into https://suno.com in a normal browser.
2. Open DevTools → Network tab, reload the page, click any request to `studio-api.suno.ai`.
3. Copy the value of the `Authorization: Bearer <...>` header (just the part after `Bearer `).
4. Pass it as `--token "<value>"`, or `export SUNO_TOKEN="<value>"` and omit the flag.

Tokens are session credentials and expire -- a `401` error from the downloader means
you need a fresh one.

## Dependencies

All scripts are pure standard-library Python except:

- `kanji_srt_maker.py` needs `whisper` on PATH (`pip install openai-whisper`), or
  `faster-whisper` (`pip install faster-whisper`) with `--engine faster-whisper`.
- `rename_photo_folders.py` uses Pillow for real EXIF dates (`pip install Pillow`);
  without it, it falls back to file mtime and prints a warning.
- `make_video.py` / `batch_video.py` need `ffmpeg` and `ffprobe` on PATH.

## Known issues and how these scripts avoid them

These are lessons from real runs of this pipeline -- read this before debugging
a weird result, it's probably one of these:

- **"Folder not found" errors in batch scripts.** `batch_karaoke.py` and
  `batch_video.py` both check the input directory exists up front and `--out-dir`
  is created with `os.makedirs(..., exist_ok=True)` before anything is written, so
  a missing output folder never silently fails partway through a batch.
- **Garbled Korean/Japanese text (encoding mismatch).** Lyric files exported from
  different tools show up in `utf-8`, `cp949`, or `shift-jis`. `batch_karaoke.py`
  tries all three automatically; the single-file scripts (`karaoke_ass_maker.py`,
  `fix_srt_timing_glitches.py`) take an explicit `--encoding` flag -- if text looks
  like `???` or mojibake, retry with `--encoding cp949` (Korean) or
  `--encoding shift-jis` (Japanese).
- **Double subtitles in VLC.** This happens when a video has subtitles burned
  into the frame *and* a soft subtitle track muxed in (or the `.ass` file is also
  loaded separately in VLC). `make_video.py` only ever burns subtitles into the
  video stream and never muxes a soft subtitle track -- don't add `-c:s mov_text`
  to the ffmpeg command, and don't load the `.ass`/`.srt` again in the player.
- **Subtitles that freeze or flash on screen.** Usually caused by SRT cues with
  zero/negative duration, overlapping cues, or cues with no gap between them --
  common output from ASR tools like whisper. Always run
  `fix_srt_timing_glitches.py` between transcription and `karaoke_ass_maker.py`;
  it enforces a minimum cue duration and a minimum gap between consecutive cues.
- **Karaoke highlight looks off / doesn't match real word timing.**
  `karaoke_ass_maker.py` splits each line's duration proportionally across
  characters -- it's an approximation for when you don't have word-level ASR
  timestamps. It looks right for most lyrics, but for a critical line, open the
  `.ass` file and hand-adjust the `\k` values (in centiseconds).

## Typical usage

```bash
# 1-2. Clean up a raw list of Suno links pasted from chat
python scripts/resolve_links.py links.txt -o resolved.txt
python scripts/dedupe_links.py resolved.txt -o deduped.txt

# 3. Download the songs
python scripts/suno_downloader.py deduped.txt --out-dir downloads/

# 4. (Only if lyrics need transcription) get Japanese kanji subtitles
python scripts/kanji_srt_maker.py downloads/song.mp3 -o downloads/song.srt

# 5. Fix timing before making karaoke
python scripts/fix_srt_timing_glitches.py downloads/song.srt -o downloads/song.fixed.srt

# 6. Build karaoke subtitles for every song in the folder
python scripts/batch_karaoke.py downloads/ --pattern "*.fixed.srt"

# 7. Render every song into a finished video
python scripts/batch_video.py downloads/ --out-dir videos/ --background "gradient:1a1a2e:16213e"
```

## Extending this skill

If you hit a new failure mode while using this pipeline, the fix belongs in two
places: the relevant script (so it doesn't happen again) and the "Known issues"
section above (so future runs of this skill know about it immediately instead of
rediscovering it). Ask the user to bump this to a new version once enough has
changed.
