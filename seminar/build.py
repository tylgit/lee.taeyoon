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
SOLO = ROOT / "standalone"

DOCS = ["textbook", "slides", "workbook", "book2"]


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


# ── 배포용 단독 파일 ──────────────────────────────────────────────
# dist/ 는 아티팩트 서버가 <head>를 붙여 주는 전제로 만든 조각이다.
# 파일만 떼어 메일·USB로 보내면 그 <head>가 없어 브라우저가 인코딩을
# 잘못 추측하고 한글이 깨진다. 그래서 배포용은 완전한 문서로 따로 쓴다.
STANDALONE_NAMES = {
    "textbook": "샬롬대학_AI교재1_처음만나는AI",
    "book2":    "샬롬대학_AI교재2_무엇이새로운가",
    "workbook": "샬롬대학_AI워크북_실습",
    "slides":   "샬롬대학_AI슬라이드_발표용",
}

SKELETON = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head}
</head>
<body>
{body}
</body>
</html>
"""


def standalone(name: str, page: str) -> str:
    """조각을 완전한 HTML 문서로 감싼다. <meta charset>은 첫 1024바이트 안에 와야
    브라우저가 본문을 읽기 전에 인코딩을 확정한다."""
    head = []
    body = page
    for tag in ("title", "style"):
        m = re.search(rf"<{tag}\b.*?</{tag}>", body, re.S)
        while m:
            head.append(m.group(0))
            body = body[: m.start()] + body[m.end():]
            m = re.search(rf"<{tag}\b.*?</{tag}>", body, re.S)
    doc = SKELETON.format(head="\n".join(head), body=body.strip())
    # 윈도우 메일 클라이언트와 탐색기가 확실히 UTF-8로 인식하도록 BOM을 붙인다
    return "\ufeff" + doc


def main():
    DIST.mkdir(exist_ok=True)
    SOLO.mkdir(exist_ok=True)
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

        solo = SOLO / f"{STANDALONE_NAMES.get(name, name)}.html"
        solo.write_text(standalone(name, out), encoding="utf-8")
        print(f"  {solo.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
