#!/usr/bin/env python3
"""세 권(교재·슬라이드·워크북)을 자체 완결 HTML 한 장으로 조립합니다.

parts/<name>.html 안의 {{css}} 와 {{fig:이름}} 자리를 채워 dist/ 에 씁니다.
아티팩트는 외부 요청이 모두 차단되므로 CSS·도표를 전부 인라인합니다.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
CSS = (ROOT / "assets" / "base.css").read_text(encoding="utf-8")
FIGS = ROOT / "parts" / "figs"
DIST = ROOT / "dist"

DOCS = ["textbook", "slides", "workbook"]


def expand(src: str) -> str:
    def fig(m):
        p = FIGS / f"{m.group(1)}.html"
        if not p.exists():
            sys.exit(f"도표 없음: {p}")
        return p.read_text(encoding="utf-8").strip()

    def part(m):
        p = ROOT / "parts" / f"{m.group(1)}.html"
        if not p.exists():
            sys.exit(f"본문 조각 없음: {p}")
        return p.read_text(encoding="utf-8").strip()

    out = src
    for _ in range(4):  # 조각 안에 또 조각/도표가 들어갈 수 있음
        out = re.sub(r"\{\{part:([a-z0-9-]+)\}\}", part, out)
        out = re.sub(r"\{\{fig:([a-z0-9-]+)\}\}", fig, out)
    return out.replace("{{css}}", CSS)


def main():
    DIST.mkdir(exist_ok=True)
    for name in DOCS:
        src = ROOT / "parts" / f"{name}.html"
        if not src.exists():
            print(f"  건너뜀 {name} (아직 없음)")
            continue
        out = expand(src.read_text(encoding="utf-8"))
        left = re.findall(r"\{\{[^}]+\}\}", out)
        if left:
            sys.exit(f"채우지 못한 자리 있음: {name} → {left[:3]}")
        dest = DIST / f"{name}.html"
        dest.write_text(out, encoding="utf-8")
        print(f"  {dest.relative_to(ROOT)}  {len(out):,} bytes")


if __name__ == "__main__":
    main()
