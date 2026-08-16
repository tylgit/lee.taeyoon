#!/usr/bin/env python3
"""Download songs (audio + lyrics + metadata) from Suno.ai share links.

Usage:
    python suno_downloader.py links.txt --out-dir downloads
    python suno_downloader.py links.txt --out-dir downloads --token "$SUNO_TOKEN"

Getting a token (only needed for songs that are not public):
    1. Log into https://suno.com in a normal browser.
    2. Open DevTools -> Network tab, reload the page, click any request to
       studio-api.suno.ai.
    3. Copy the value of the "Authorization: Bearer <...>" request header
       (just the token after "Bearer ").
    4. Pass it as --token, or set the SUNO_TOKEN environment variable.
    A token is a session credential and expires after a while -- if
    downloads start failing with 401, grab a fresh one.

Each song produces three files in --out-dir, named after the sanitized song
title and clip id:
    <title>__<clip_id>.mp3   the audio
    <title>__<clip_id>.txt   the lyrics, if Suno returned any
    <title>__<clip_id>.json  full metadata (useful for kanji_srt_maker /
                              karaoke_ass_maker downstream)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://studio-api.suno.ai/api/clip"
SONG_ID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)


def extract_clip_id(url_or_id):
    m = SONG_ID_RE.search(url_or_id)
    if not m:
        raise ValueError(f"Could not find a Suno clip id in: {url_or_id}")
    return m.group(1)


def sanitize(name, max_len=80):
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()
    name = re.sub(r"\s+", " ", name)
    return (name or "untitled")[:max_len]


def fetch_json(url, token, timeout):
    headers = {"User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url, dest, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def process_one(clip_id, out_dir, token, timeout):
    meta = fetch_json(f"{API_BASE}/{clip_id}", token, timeout)

    title = sanitize(meta.get("title") or clip_id)
    base = os.path.join(out_dir, f"{title}__{clip_id}")

    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    lyrics = (meta.get("metadata") or {}).get("prompt") or meta.get("lyrics")
    if lyrics:
        with open(base + ".txt", "w", encoding="utf-8") as f:
            f.write(lyrics.strip() + "\n")

    audio_url = meta.get("audio_url")
    if not audio_url:
        raise RuntimeError("No audio_url in response -- song may still be generating, or the token is missing/expired")
    download_file(audio_url, base + ".mp3", timeout)

    return base + ".mp3"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="text file with one Suno song URL (or bare clip id) per line")
    ap.add_argument("--out-dir", required=True, help="directory to write downloaded files into")
    ap.add_argument("--token", default=os.environ.get("SUNO_TOKEN"), help="Suno bearer token (or set SUNO_TOKEN env var); required for private songs")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds to sleep between songs, to be polite to the API")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    with open(args.input, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

    ok, failed = 0, []
    for i, line in enumerate(lines, 1):
        try:
            clip_id = extract_clip_id(line)
            path = process_one(clip_id, args.out_dir, args.token, args.timeout)
            print(f"[{i}/{len(lines)}] OK: {path}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"[{i}/{len(lines)}] FAILED ({e.code}): {line}", file=sys.stderr)
            if e.code == 401:
                print("  -> token missing or expired, see --help for how to get one", file=sys.stderr)
            failed.append(line)
        except Exception as e:
            print(f"[{i}/{len(lines)}] FAILED: {line} ({e})", file=sys.stderr)
            failed.append(line)
        time.sleep(args.delay)

    print(f"\nDone: {ok} succeeded, {len(failed)} failed", file=sys.stderr)
    if failed:
        fail_path = os.path.join(args.out_dir, "failed_links.txt")
        with open(fail_path, "w", encoding="utf-8") as f:
            f.write("\n".join(failed) + "\n")
        print(f"Failed links written to {fail_path} -- fix and re-run just that file", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
