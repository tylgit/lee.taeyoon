#!/usr/bin/env python3
"""Deduplicate a list of URLs, normalizing away cosmetic differences so
near-identical links (tracking params, trailing slash, http vs https,
www vs no-www) collapse to one entry.

Usage:
    python dedupe_links.py links.txt -o deduped.txt

Run this *after* resolve_links.py so redirected duplicates are already
pointing at the same final URL.
"""
import argparse
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "igshid", "si", "ref")


def normalize(url):
    parts = urlsplit(url.strip())
    scheme = "https"  # treat http/https as equivalent
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path.rstrip("/") or "/"

    kept_query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not any(k.lower() == p or k.lower().startswith(p) for p in TRACKING_PREFIXES)
    ]
    query = urlencode(sorted(kept_query))

    return urlunsplit((scheme, netloc, path, query, ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="text file with one URL per line")
    ap.add_argument("-o", "--output", help="output file (default: stdout)")
    args = ap.parse_args()

    seen = set()
    kept = []
    dropped = 0
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith("#"):
                continue
            key = normalize(url)
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            kept.append(url)

    out = "\n".join(kept) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    print(f"{len(kept)} unique links kept, {dropped} duplicates dropped", file=sys.stderr)


if __name__ == "__main__":
    main()
