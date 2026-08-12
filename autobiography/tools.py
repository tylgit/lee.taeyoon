#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자서전 만들기 도구.

사용법:
  python3 tools.py init            답변 파일 90개를 answers/ 에 만든다 (이미 있으면 건너뜀)
  python3 tools.py status          답변 진행 상황을 보여 준다
  python3 tools.py next            아직 답하지 않은 다음 질문을 보여 준다
  python3 tools.py build           답을 모아 완성본 책을 book/output/ 에 만든다
  python3 tools.py build --qa      (장 원고가 있어도) 질문·답 모음 형식으로 만든다

원칙: 이 스크립트는 조립만 한다. 문장을 고치거나 지어내지 않는다.
교정과 윤문은 클로드가 /interview 와 /book-build 스킬에서 사람과 함께 한다.
"""
import json, os, re, shutil, subprocess, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(BASE, "answers")
CHAPTERS = os.path.join(BASE, "book", "chapters")
OUTPUT = os.path.join(BASE, "book", "output")
META = os.path.join(BASE, "book", "meta.md")
CSS = os.path.join(BASE, "book", "book.css")

STATUSES = ["미답변", "원문", "다듬음", "확정", "건너뜀"]

def load_questions():
    with open(os.path.join(BASE, "questions.json"), encoding="utf-8") as f:
        return json.load(f)

def answer_path(sec_id, n):
    return os.path.join(ANSWERS, f"{sec_id}{n:02d}.md")

TEMPLATE = """# {sid}-{n:02d}. {q}

상태: 미답변

## 말한 그대로 (원문)

(아직 없음)

## 다듬은 글

(아직 없음)

## 메모 (사진, 확인할 연도·이름 등)

"""

def cmd_init():
    os.makedirs(ANSWERS, exist_ok=True)
    data = load_questions()
    made = 0
    for sec in data["sections"]:
        for item in sec["questions"]:
            p = answer_path(sec["id"], item["n"])
            if not os.path.exists(p):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(TEMPLATE.format(sid=sec["id"], n=item["n"], q=item["q"]))
                made += 1
    print(f"답변 파일 {made}개 생성 (전체 90개 중). 위치: {ANSWERS}")

def parse_answer(path):
    """답변 파일에서 상태, 원문, 다듬은 글을 뽑아 낸다."""
    if not os.path.exists(path):
        return {"status": "미답변", "raw": "", "polished": ""}
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^상태:\s*(\S+)", text, re.M)
    status = m.group(1) if m else "미답변"
    def section(name):
        pat = rf"^## {name}.*?\n(.*?)(?=^## |\Z)"
        mm = re.search(pat, text, re.M | re.S)
        if not mm:
            return ""
        body = mm.group(1).strip()
        if body in ("(아직 없음)", ""):
            return ""
        return body
    return {"status": status, "raw": section("말한 그대로"), "polished": section("다듬은 글")}

def cmd_status():
    data = load_questions()
    total = answered = polished = skipped = 0
    print("묶음별 진행 상황")
    for sec in data["sections"]:
        marks = []
        for item in sec["questions"]:
            a = parse_answer(answer_path(sec["id"], item["n"]))
            total += 1
            if a["status"] == "건너뜀":
                skipped += 1; marks.append("−")
            elif a["polished"]:
                polished += 1; answered += 1; marks.append("●")
            elif a["raw"]:
                answered += 1; marks.append("◐")
            else:
                marks.append("○")
        print(f"  {sec['id']}. {sec['title'][:20]:<22} {' '.join(marks)}")
    print(f"\n전체 {total}문 | 답함 {answered} (다듬음 {polished}) | 건너뜀 {skipped} | 남음 {total - answered - skipped}")
    print("표시: ● 다듬은 글 있음  ◐ 원문만 있음  ○ 미답변  − 건너뜀")

def cmd_next():
    data = load_questions()
    for sec in data["sections"]:
        for item in sec["questions"]:
            a = parse_answer(answer_path(sec["id"], item["n"]))
            if a["status"] != "건너뜀" and not a["raw"] and not a["polished"]:
                print(f"{sec['id']}-{item['n']:02d} [{sec['title']}]")
                print(item["q"])
                return
    print("모든 질문에 답하셨습니다! 이제 build 로 책을 만드십시오.")

def read_meta():
    meta = {"제목": "나의 이야기", "지은이": "", "머리말": "", "부제": ""}
    if os.path.exists(META):
        text = open(META, encoding="utf-8").read()
        for key in ("제목", "부제", "지은이"):
            m = re.search(rf"^{key}:\s*(.+)$", text, re.M)
            if m and m.group(1).strip() and not m.group(1).strip().startswith("("):
                meta[key] = m.group(1).strip()
        m = re.search(r"^## 머리말\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if m:
            body = m.group(1).strip()
            if body and not body.startswith("("):
                meta["머리말"] = body
    return meta

def cmd_build(force_qa=False):
    data = load_questions()
    meta = read_meta()
    os.makedirs(OUTPUT, exist_ok=True)
    lines = []
    lines.append(f"# {meta['제목']}")
    if meta["부제"]:
        lines.append(f"\n**{meta['부제']}**")
    if meta["지은이"]:
        lines.append(f"\n{meta['지은이']} 지음")
    lines.append("\n---\n")
    if meta["머리말"]:
        lines.append("## 머리말\n")
        lines.append(meta["머리말"])
        lines.append("\n---\n")

    chapter_files = sorted(glob.glob(os.path.join(CHAPTERS, "*.md"))) if not force_qa else []
    used_chapters = False
    if chapter_files:
        used_chapters = True
        for cf in chapter_files:
            lines.append(open(cf, encoding="utf-8").read().strip())
            lines.append("\n")
    else:
        empty = True
        for idx, sec in enumerate(data["sections"], 1):
            body = []
            for item in sec["questions"]:
                a = parse_answer(answer_path(sec["id"], item["n"]))
                text = a["polished"] or a["raw"]
                if not text or a["status"] == "건너뜀":
                    continue
                body.append(f"### {item['q']}\n\n{text}\n")
            if body:
                empty = False
                lines.append(f"## 제{idx}장. {sec['title']}\n")
                if sec.get("intro"):
                    lines.append(f"*{sec['intro']}*\n")
                lines.extend(body)
        if empty:
            print("아직 답변이 하나도 없습니다. /interview 로 먼저 답을 모으십시오.")
            return 1

    book_md = os.path.join(OUTPUT, "자서전_완성본.md")
    with open(book_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")
    mode = "장 원고(chapters/)" if used_chapters else "질문·답 모음(answers/)"
    print(f"조립 완료 ({mode} 기준) → {book_md}")

    html = os.path.join(OUTPUT, "자서전_완성본.html")
    docx = os.path.join(OUTPUT, "자서전_완성본.docx")
    pdf = os.path.join(OUTPUT, "자서전_완성본.pdf")
    if shutil.which("pandoc"):
        css_args = ["--embed-resources", "-c", CSS] if os.path.exists(CSS) else []
        subprocess.run(["pandoc", "-s", *css_args, "--metadata", f"pagetitle={meta['제목']}",
                        book_md, "-o", html], check=True)
        subprocess.run(["pandoc", book_md, "-o", docx], check=True)
        print(f"변환 완료 → {html}\n변환 완료 → {docx}")
    else:
        print("pandoc이 없어 HTML/DOCX 변환은 건너뜁니다. (apt-get install pandoc)")
    chrome = (shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
              or next(iter(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")), None))
    if chrome and os.path.exists(html):
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                        f"file://{html}"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"변환 완료 → {pdf}")
    else:
        print("크로미움이 없어 PDF 변환은 건너뜁니다.")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "init":
        cmd_init()
    elif cmd == "status":
        cmd_status()
    elif cmd == "next":
        cmd_next()
    elif cmd == "build":
        sys.exit(cmd_build(force_qa="--qa" in sys.argv))
    else:
        print(__doc__)
