#!/usr/bin/env python3
"""Batch-export your own Suno songs: mp3 + srt + lrc + word-level timing JSON + metadata.

Suno has no official public API. This talks to the same unofficial endpoints the
suno.com web app itself calls, authenticated with your own browser session cookie.
Only use this on your own account / your own generated songs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
STUDIO_API = "https://studio-api.prod.suno.com"
CLERK_API_VERSION = "2021-02-05"
CLERK_DOMAINS = ["clerk.suno.com", "auth.suno.com"]

REQUEST_DELAY = float(os.environ.get("SUNO_REQUEST_DELAY", "0.8"))
TOKEN_TTL = 50  # seconds; Clerk session tokens expire around 60s


class AuthError(RuntimeError):
    pass


class TokenManager:
    """Fetches and periodically refreshes the short-lived Clerk bearer token."""

    def __init__(self, cookie: str, clerk_domain: str | None = None):
        self.cookie = cookie
        self.clerk_domains = [clerk_domain] if clerk_domain else CLERK_DOMAINS
        self._session_id = None
        self._token = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()
        self._resolved_domain = None

    def _headers(self):
        return {"User-Agent": USER_AGENT, "Cookie": self.cookie}

    def _try_domains(self, fn):
        domains = [self._resolved_domain] if self._resolved_domain else self.clerk_domains
        last_err = None
        for domain in domains:
            try:
                result = fn(domain)
                self._resolved_domain = domain
                return result
            except Exception as e:  # noqa: BLE001
                last_err = e
        raise AuthError(f"Could not reach Clerk auth on any domain: {last_err}")

    def _fetch_session_id(self):
        def go(domain):
            r = requests.get(
                f"https://{domain}/v1/client",
                params={"__clerk_api_version": CLERK_API_VERSION},
                headers=self._headers(),
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            payload = data.get("response", data)
            sessions = payload.get("sessions") or []
            if not sessions:
                raise AuthError("No active Suno session found in cookie (are you logged in?)")
            return sessions[0]["id"]

        return self._try_domains(go)

    def _refresh(self):
        if self._session_id is None:
            self._session_id = self._fetch_session_id()

        def go(domain):
            r = requests.post(
                f"https://{domain}/v1/client/sessions/{self._session_id}/tokens",
                params={"__clerk_api_version": CLERK_API_VERSION},
                headers=self._headers(),
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            token = data.get("jwt") or data.get("response", {}).get("jwt")
            if not token:
                raise AuthError("Clerk token refresh did not return a jwt")
            return token

        self._token = self._try_domains(go)
        self._fetched_at = time.time()

    def get_token(self) -> str:
        with self._lock:
            if self._token is None or (time.time() - self._fetched_at) > TOKEN_TTL:
                self._refresh()
            return self._token

    def auth_headers(self):
        return {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {self.get_token()}",
        }


def sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", name).strip()
    name = re.sub(r"\s+", " ", name)
    return name[:max_len] if name else "untitled"


def api_get(path: str, tm: TokenManager, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(f"{STUDIO_API}{path}", headers=tm.auth_headers(), params=params, timeout=30)
            if r.status_code == 401:
                tm._token = None  # force refresh and retry
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {path} failed after {retries} attempts: {last_err}")


def fetch_all_clips(tm: TokenManager, limit: int | None, log) -> list[dict]:
    clips = []
    seen_ids = set()
    page = 0
    max_empty_pages = 2
    empty_streak = 0
    while True:
        r = api_get("/api/feed/v2", tm, params={"page": page})
        data = r.json()
        page_clips = data.get("clips") or data.get("data") or []
        new_clips = [c for c in page_clips if c.get("id") not in seen_ids]
        if not new_clips:
            empty_streak += 1
            if empty_streak >= max_empty_pages:
                break
        else:
            empty_streak = 0
            for c in new_clips:
                seen_ids.add(c["id"])
                clips.append(c)
            log(f"  page {page}: +{len(new_clips)} clips (total {len(clips)})")
        page += 1
        if limit and len(clips) >= limit:
            clips = clips[:limit]
            break
        if page > 2000:
            break
        time.sleep(REQUEST_DELAY)
    return clips


def fetch_aligned_words(clip_id: str, tm: TokenManager, max_retries=8, delay=3.0):
    for attempt in range(max_retries):
        try:
            r = api_get(f"/api/gen/{clip_id}/aligned_lyrics/v2/", tm)
        except RuntimeError:
            return None
        data = r.json()
        words = data.get("aligned_words") or data.get("alignedWords")
        if words:
            return words
        time.sleep(delay)
    return None


def normalize_word(w: dict) -> dict:
    return {
        "text": w.get("word", w.get("text", "")),
        "start": w.get("start_s", w.get("startS", 0.0)),
        "end": w.get("end_s", w.get("endS", 0.0)),
    }


def group_words_into_lines(words: list[dict], gap_threshold=0.6) -> list[list[dict]]:
    lines: list[list[dict]] = []
    current: list[dict] = []
    prev_end = None
    for raw in words:
        w = normalize_word(raw)
        if prev_end is not None and (w["start"] - prev_end) > gap_threshold and current:
            lines.append(current)
            current = []
        current.append(w)
        prev_end = w["end"]
    if current:
        lines.append(current)
    return lines


def format_srt_time(t: float) -> str:
    ms_total = int(round(t * 1000))
    h, ms_total = divmod(ms_total, 3600_000)
    m, ms_total = divmod(ms_total, 60_000)
    s, ms = divmod(ms_total, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_lrc_time(t: float) -> str:
    m = int(t // 60)
    s = t - m * 60
    return f"[{m:02d}:{s:05.2f}]"


def write_srt(lines: list[list[dict]], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines, 1):
            text = " ".join(w["text"] for w in line).strip()
            if not text:
                continue
            f.write(f"{i}\n{format_srt_time(line[0]['start'])} --> {format_srt_time(line[-1]['end'])}\n{text}\n\n")


def write_lrc(lines: list[list[dict]], path: Path, title: str | None = None):
    with open(path, "w", encoding="utf-8") as f:
        if title:
            f.write(f"[ti:{title}]\n")
        for line in lines:
            text = " ".join(w["text"] for w in line).strip()
            if not text:
                continue
            f.write(f"{format_lrc_time(line[0]['start'])}{text}\n")


def download_file(url: str, path: Path, retries=3) -> bool:
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = path.with_suffix(path.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 15):
                        if chunk:
                            f.write(chunk)
                tmp.rename(path)
            return True
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                return False
            time.sleep(2 ** attempt)
    return False


def load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_manifest(path: Path, manifest: dict):
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def process_clip(clip: dict, out_dir: Path, tm: TokenManager, overwrite: bool, log) -> dict:
    clip_id = clip.get("id", "unknown")
    title = clip.get("title") or clip.get("metadata", {}).get("prompt", "")[:40] or "untitled"
    status = clip.get("status")
    folder = out_dir / sanitize_filename(f"{title}__{clip_id}")
    folder.mkdir(parents=True, exist_ok=True)

    entry = {"id": clip_id, "title": title, "status": status}

    meta_path = folder / "metadata.json"
    if overwrite or not meta_path.exists():
        meta_path.write_text(json.dumps(clip, ensure_ascii=False, indent=2), encoding="utf-8")

    if status != "complete":
        entry["mp3"] = "skipped (not complete)"
        entry["lyrics"] = "skipped"
        return entry

    audio_url = clip.get("audio_url")
    mp3_path = folder / "song.mp3"
    if audio_url and (overwrite or not mp3_path.exists()):
        ok = download_file(audio_url, mp3_path)
        entry["mp3"] = "ok" if ok else "failed"
    elif mp3_path.exists():
        entry["mp3"] = "cached"
    else:
        entry["mp3"] = "no audio_url"

    words_path = folder / "words.json"
    srt_path = folder / "lyrics.srt"
    lrc_path = folder / "lyrics.lrc"
    if not overwrite and words_path.exists() and srt_path.exists() and lrc_path.exists():
        entry["lyrics"] = "cached"
        return entry

    words = fetch_aligned_words(clip_id, tm)
    if words:
        lines = group_words_into_lines(words)
        words_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
        write_srt(lines, srt_path)
        write_lrc(lines, lrc_path, title=title)
        entry["lyrics"] = "ok"
    else:
        entry["lyrics"] = "unavailable"
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cookie", default=os.environ.get("SUNO_COOKIE"),
                     help="Full Cookie header value copied from a logged-in suno.com browser session "
                          "(or set SUNO_COOKIE env var)")
    ap.add_argument("--out-dir", default="./suno_downloads")
    ap.add_argument("--limit", type=int, default=None, help="Only process the first N songs (for testing)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--list-only", action="store_true", help="Only fetch and save the song list, no downloads")
    ap.add_argument("--clerk-domain", default=None, help="Override Clerk auth domain if auto-detect fails")
    ap.add_argument("--test-auth", action="store_true", help="Just verify the cookie works and exit")
    args = ap.parse_args()

    if not args.cookie:
        print("ERROR: pass --cookie or set SUNO_COOKIE env var. See README_SUNO.md for how to get it.",
              file=sys.stderr)
        sys.exit(1)

    def log(msg):
        print(msg, flush=True)

    tm = TokenManager(args.cookie, clerk_domain=args.clerk_domain)

    if args.test_auth:
        try:
            tm.get_token()
            r = api_get("/api/billing/info/", tm)
            log("Auth OK. Billing info:")
            log(json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception as e:  # noqa: BLE001
            log(f"Auth FAILED: {e}")
            sys.exit(1)
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log("Fetching song list from Suno...")
    clips = fetch_all_clips(tm, args.limit, log)
    log(f"Found {len(clips)} songs.")
    (out_dir / "clips_raw.json").write_text(json.dumps(clips, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.list_only:
        log("--list-only set, stopping here.")
        return

    manifest_path = out_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    manifest_lock = threading.Lock()

    todo = [c for c in clips if args.overwrite or c.get("id") not in manifest]
    log(f"Downloading {len(todo)} songs ({len(clips) - len(todo)} already in manifest)...")

    done_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_clip, c, out_dir, tm, args.overwrite, log): c for c in todo}
        for fut in as_completed(futures):
            clip = futures[fut]
            try:
                entry = fut.result()
            except Exception as e:  # noqa: BLE001
                entry = {"id": clip.get("id"), "title": clip.get("title"), "error": str(e)}
            with manifest_lock:
                manifest[entry["id"]] = entry
                save_manifest(manifest_path, manifest)
            done_count += 1
            log(f"[{done_count}/{len(todo)}] {entry.get('title', '?')} -> mp3={entry.get('mp3')} lyrics={entry.get('lyrics')}")

    failed = [e for e in manifest.values() if e.get("mp3") == "failed" or e.get("error")]
    log(f"\nDone. {len(manifest)} songs recorded in manifest.json, {len(failed)} with problems.")
    if failed:
        log("Songs with problems (see manifest.json for details):")
        for e in failed[:20]:
            log(f"  - {e.get('title')} ({e.get('id')})")


if __name__ == "__main__":
    main()
