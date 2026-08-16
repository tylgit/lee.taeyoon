#!/usr/bin/env python3
"""Resolve shortened / redirected URLs (e.g. share links) to their final destination.

Usage:
    python resolve_links.py links.txt -o resolved.txt
    python resolve_links.py links.txt --timeout 10

Input: a text file with one URL per line (blank lines and lines starting with
# are ignored). Output: one resolved URL per line, in the same order as the
input. Lines that fail to resolve are kept as-is and reported on stderr so
nothing silently disappears from the list.
"""
import argparse
import sys
import urllib.error
import urllib.request


def read_links(path):
    links = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            links.append(line)
    return links


def resolve(url, timeout):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.geturl()
    except urllib.error.HTTPError as e:
        # Some servers (e.g. Suno) reject HEAD; fall back to a real GET.
        if e.code in (403, 405):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.geturl()
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="text file with one URL per line")
    ap.add_argument("-o", "--output", help="output file (default: stdout)")
    ap.add_argument("--timeout", type=float, default=10.0, help="per-request timeout in seconds (default 10)")
    args = ap.parse_args()

    links = read_links(args.input)
    if not links:
        print(f"No links found in {args.input}", file=sys.stderr)
        sys.exit(1)

    resolved = []
    failures = 0
    for i, url in enumerate(links, 1):
        try:
            final_url = resolve(url, args.timeout)
            resolved.append(final_url)
            if final_url != url:
                print(f"[{i}/{len(links)}] {url} -> {final_url}", file=sys.stderr)
        except Exception as e:
            print(f"[{i}/{len(links)}] FAILED to resolve {url}: {e}", file=sys.stderr)
            resolved.append(url)
            failures += 1

    out = "\n".join(resolved) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {len(resolved)} links to {args.output} ({failures} failed to resolve)", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
