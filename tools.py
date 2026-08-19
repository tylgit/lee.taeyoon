#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자서전 만들기 도구 모음.

파이썬 표준 라이브러리만 사용합니다. 따로 설치할 것이 없습니다.

    python3 tools.py status   # 답변 현황 보기
    python3 tools.py new      # 빈 답변지 만들기 (없는 장만)
    python3 tools.py build    # 책 조립 (워드/PDF/HTML)
    python3 tools.py zip      # 자서전_시작폴더.zip 다시 만들기
"""

import html
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
ANSWER_DIR = os.path.join(ROOT, "interview", "answers")
QUESTION_FILE = os.path.join(ROOT, "interview", "questions.md")
CHAPTER_DIR = os.path.join(ROOT, "book", "chapters")
META_FILE = os.path.join(ROOT, "book", "meta.md")
OUTPUT_DIR = os.path.join(ROOT, "book", "output")

UNANSWERED = "(아직 답변 전)"

CHAPTER_TITLES = [
    "뿌리와 태어난 곳",
    "어린 시절",
    "학창 시절",
    "청년의 문턱",
    "사랑과 결혼",
    "일과 생업",
    "자녀와 가족",
    "시련과 이겨낸 힘",
    "믿음과 마음의 뿌리",
    "벗과 이웃, 고마운 사람들",
    "지금의 하루",
    "남기고 싶은 말",
]


# ---------------------------------------------------------------- 공통 도우미

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def safe_name(text):
    """파일 이름으로 쓸 수 없는 글자를 걸러 냅니다."""
    text = unicodedata.normalize("NFC", text).strip()
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "자서전"


def chapter_files():
    if not os.path.isdir(CHAPTER_DIR):
        return []
    names = [n for n in os.listdir(CHAPTER_DIR) if n.endswith(".md")]
    return [os.path.join(CHAPTER_DIR, n) for n in sorted(names)]


def answer_files():
    if not os.path.isdir(ANSWER_DIR):
        return []
    names = [n for n in os.listdir(ANSWER_DIR) if n.endswith(".md")]
    return [os.path.join(ANSWER_DIR, n) for n in sorted(names)]


# ------------------------------------------------------------------- status

def parse_answer_file(path):
    """답변지 한 장을 읽어 (장 제목, [(질문, 답변), ...]) 로 돌려줍니다."""
    title = os.path.basename(path)
    items = []
    question = None
    body = []
    for line in read(path).splitlines():
        if line.startswith("# ") and question is None and not items:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if question is not None:
                items.append((question, "\n".join(body).strip()))
            question = line[3:].strip()
            body = []
        elif question is not None:
            body.append(line)
    if question is not None:
        items.append((question, "\n".join(body).strip()))
    return title, items


def is_answered(answer):
    stripped = answer.strip()
    if not stripped:
        return False
    if stripped.startswith(UNANSWERED):
        return False
    return True


def cmd_status(argv):
    files = answer_files()
    if not files:
        print("아직 답변지가 없습니다.")
        print("먼저 '인터뷰 시작해 줘' 라고 말씀해 주세요.")
        print("(또는  python3 tools.py new  를 실행하면 빈 답변지가 만들어집니다.)")
        return 0

    total = done = 0
    print("답변 현황")
    print("=" * 46)
    for path in files:
        title, items = parse_answer_file(path)
        d = sum(1 for _, a in items if is_answered(a))
        total += len(items)
        done += d
        if not items:
            mark = "  "
        elif d == len(items):
            mark = "완료"
        elif d == 0:
            mark = "   -"
        else:
            mark = "진행"
        print("%-4s %-24s %2d / %2d" % (mark, title, d, len(items)))
    print("=" * 46)
    pct = (done * 100 // total) if total else 0
    print("모두 합쳐 %d / %d 문항 (%d%%)" % (done, total, pct))

    written = len(chapter_files())
    print("원고가 써진 장: %d / %d" % (written, len(CHAPTER_TITLES)))
    if done and done == total:
        print("\n답변이 모두 채워졌습니다. '책으로 만들어 줘' 라고 말씀해 주세요.")
    elif done:
        print("\n남은 질문을 이어가려면 '인터뷰 이어서 해 줘' 라고 말씀해 주세요.")
    return 0


# ---------------------------------------------------------------------- new

def cmd_new(argv):
    """질문 목록을 보고 빈 답변지를 만듭니다. 이미 있는 파일은 건드리지 않습니다."""
    if not os.path.exists(QUESTION_FILE):
        print("질문 목록(interview/questions.md)이 없습니다.")
        return 1

    chapters = []       # [(번호, 제목, [질문...])]
    num = title = None
    questions = []
    for line in read(QUESTION_FILE).splitlines():
        m = re.match(r"^##\s*(\d+)장[.\s]*(.*)$", line.strip())
        if m:
            if num is not None:
                chapters.append((num, title, questions))
            num, title, questions = int(m.group(1)), m.group(2).strip(), []
            continue
        m = re.match(r"^\s*\d+[.)]\s+(.*\S)\s*$", line)
        if m and num is not None:
            questions.append(m.group(1).strip())
    if num is not None:
        chapters.append((num, title, questions))

    made = 0
    for num, title, questions in chapters:
        path = os.path.join(ANSWER_DIR, "ch%02d.md" % num)
        if os.path.exists(path):
            continue
        lines = ["# %d장 %s" % (num, title), ""]
        for i, q in enumerate(questions, 1):
            lines += ["## Q%d. %s" % (i, q), "", UNANSWERED, ""]
        write(path, "\n".join(lines))
        made += 1
        print("만듦: interview/answers/ch%02d.md  (질문 %d개)" % (num, len(questions)))
    if not made:
        print("빈 답변지를 새로 만들 것이 없습니다. (이미 다 있습니다)")
    return 0


# ------------------------------------------------------- 아주 작은 마크다운 해석기

def parse_markdown(text):
    """블록 목록으로 바꿉니다. ('h1'|'h2'|'p'|'quote'|'hr', 내용)"""
    blocks = []
    buffer = []

    def flush(kind="p"):
        if buffer:
            blocks.append((kind, " ".join(buffer).strip()))
            del buffer[:]

    quoting = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush("quote" if quoting else "p")
            quoting = False
            continue
        if stripped in ("---", "***", "* * *"):
            flush("quote" if quoting else "p")
            quoting = False
            blocks.append(("hr", ""))
            continue
        if stripped.startswith("# "):
            flush("quote" if quoting else "p")
            quoting = False
            blocks.append(("h1", stripped[2:].strip()))
            continue
        if stripped.startswith("## "):
            flush("quote" if quoting else "p")
            quoting = False
            blocks.append(("h2", stripped[3:].strip()))
            continue
        if stripped.startswith(">"):
            if not quoting:
                flush("p")
                quoting = True
            buffer.append(stripped.lstrip(">").strip())
            continue
        if quoting:
            flush("quote")
            quoting = False
        buffer.append(stripped)
    flush("quote" if quoting else "p")
    return blocks


def split_inline(text):
    """굵게/기울임 표시를 (글자, 굵게, 기울임) 조각으로 나눕니다."""
    parts = []
    pattern = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)", re.S)
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            parts.append((text[pos:m.start()], False, False))
        chunk = m.group(0)
        if chunk.startswith("**"):
            parts.append((chunk[2:-2], True, False))
        else:
            parts.append((chunk[1:-1], False, True))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], False, False))
    return parts or [(text, False, False)]


# ---------------------------------------------------------------- 원고 모으기

def load_meta():
    meta = {
        "제목": "나의 이야기",
        "부제": "",
        "지은이": "",
        "엮은이": "",
        "펴낸날": date.today().strftime("%Y년 %m월"),
    }
    preface = ""
    if os.path.exists(META_FILE):
        text = read(META_FILE)
        m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k:
                        meta[k] = v
            preface = m.group(2).strip()
        else:
            preface = text.strip()
    meta = {k: v for k, v in meta.items() if v}
    return meta, preface


def load_book():
    """(meta, 머리말 블록, [(장 제목, 블록들), ...]) 를 돌려줍니다."""
    meta, preface_md = load_meta()
    preface = parse_markdown(preface_md) if preface_md else []
    if preface and preface[0][0] == "h1":
        preface = preface[1:]

    chapters = []
    for path in chapter_files():
        blocks = parse_markdown(read(path))
        title = os.path.splitext(os.path.basename(path))[0]
        if blocks and blocks[0][0] == "h1":
            title = blocks[0][1]
            blocks = blocks[1:]
        chapters.append((title, blocks))
    return meta, preface, chapters


# ---------------------------------------------------------------------- HTML

HTML_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0;
  background: #f6f3ec; color: #23211d;
  font-family: "본명조", "NanumMyeongjo", "Nanum Myeongjo", "나눔명조",
               "바탕", Batang, "맑은 고딕", "Malgun Gothic",
               "Apple SD Gothic Neo", serif;
  font-size: 20px; line-height: 1.9;
}
.page { max-width: 42rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; }
.cover { text-align: center; padding: 6rem 1.5rem 5rem; border-bottom: 1px solid #d8d0c0; }
.cover h1 { font-size: 2.6rem; line-height: 1.4; margin: 0 0 .8rem; letter-spacing: .02em; }
.cover .sub { font-size: 1.2rem; color: #6b6357; margin: 0 0 3rem; }
.cover .by { font-size: 1.15rem; margin: 0; }
.cover .date { font-size: .95rem; color: #6b6357; margin-top: .6rem; }
h2.chapter { font-size: 1.7rem; margin: 4rem 0 2rem; padding-top: 2rem;
             border-top: 1px solid #d8d0c0; page-break-before: always; }
h2.chapter .no { display: block; font-size: .85rem; letter-spacing: .3em;
                 color: #8a8070; margin-bottom: .6rem; }
h3 { font-size: 1.2rem; margin: 2.5rem 0 1rem; color: #4a443a; }
p { margin: 0 0 1.2rem; text-align: justify; }
blockquote { margin: 1.8rem 0; padding: .2rem 0 .2rem 1.2rem;
             border-left: 3px solid #c9bfa8; color: #4a443a; font-style: normal; }
hr.scene { border: 0; text-align: center; margin: 2.4rem 0; }
hr.scene::after { content: "· · ·"; letter-spacing: .6em; color: #a89e8b; }
nav.toc { margin: 3rem 0 0; page-break-after: always; }
nav.toc h2 { font-size: 1.4rem; margin: 0 0 1.2rem; }
nav.toc ol { padding-left: 1.4rem; }
nav.toc li { margin: .4rem 0; }
nav.toc a { color: #23211d; text-decoration: none; }
@media print {
  body { background: #fff; font-size: 11pt; }
  .page { max-width: none; padding: 0; }
}
"""


def blocks_to_html(blocks, heading_tag="h3"):
    out = []
    for kind, content in blocks:
        if kind == "hr":
            out.append('<hr class="scene">')
        elif kind in ("h1", "h2"):
            out.append("<%s>%s</%s>" % (heading_tag, inline_html(content), heading_tag))
        elif kind == "quote":
            out.append("<blockquote><p>%s</p></blockquote>" % inline_html(content))
        else:
            out.append("<p>%s</p>" % inline_html(content))
    return "\n".join(out)


def inline_html(text):
    out = []
    for chunk, bold, italic in split_inline(text):
        piece = html.escape(chunk)
        if bold:
            piece = "<strong>%s</strong>" % piece
        if italic:
            piece = "<em>%s</em>" % piece
        out.append(piece)
    return "".join(out)


def build_html(meta, preface, chapters, path):
    title = meta.get("제목", "나의 이야기")
    parts = ["<!DOCTYPE html>", '<html lang="ko">', "<head>",
             '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             "<title>%s</title>" % html.escape(title),
             "<style>%s</style>" % HTML_CSS,
             "</head>", "<body>",
             '<header class="cover">',
             "<h1>%s</h1>" % html.escape(title)]
    if meta.get("부제"):
        parts.append('<p class="sub">%s</p>' % html.escape(meta["부제"]))
    if meta.get("지은이"):
        parts.append('<p class="by">%s 지음</p>' % html.escape(meta["지은이"]))
    if meta.get("엮은이"):
        parts.append('<p class="date">%s 엮음</p>' % html.escape(meta["엮은이"]))
    if meta.get("펴낸날"):
        parts.append('<p class="date">%s</p>' % html.escape(meta["펴낸날"]))
    parts.append("</header>")
    parts.append('<main class="page">')

    if preface:
        parts.append('<h2 class="chapter" id="preface">머리말</h2>')
        parts.append(blocks_to_html(preface))

    if chapters:
        parts.append('<nav class="toc"><h2>차례</h2><ol>')
        for i, (ct, _) in enumerate(chapters, 1):
            parts.append('<li><a href="#ch%d">%s</a></li>' % (i, html.escape(ct)))
        parts.append("</ol></nav>")

    for i, (ct, blocks) in enumerate(chapters, 1):
        parts.append('<h2 class="chapter" id="ch%d"><span class="no">제 %d 장</span>%s</h2>'
                     % (i, i, html.escape(ct)))
        parts.append(blocks_to_html(blocks))

    parts += ["</main>", "</body>", "</html>"]
    write(path, "\n".join(parts))


# ---------------------------------------------------------------------- DOCX

def xml_escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def run_xml(text, bold=False, italic=False, size=None, color=None):
    props = ['<w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic"'
             ' w:eastAsia="맑은 고딕" w:cs="Malgun Gothic"/>']
    if bold:
        props.append("<w:b/><w:bCs/>")
    if italic:
        props.append("<w:i/><w:iCs/>")
    if color:
        props.append('<w:color w:val="%s"/>' % color)
    if size:
        props.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size))
    return ('<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>'
            % ("".join(props), xml_escape(text)))


def para_xml(text, style="Body", align=None, page_break=False, size=None,
             bold=False, color=None, spacing_before=None):
    props = ['<w:pStyle w:val="%s"/>' % style]
    if page_break:
        props.append("<w:pageBreakBefore/>")
    if spacing_before is not None:
        props.append('<w:spacing w:before="%d"/>' % spacing_before)
    if align:
        props.append('<w:jc w:val="%s"/>' % align)
    runs = []
    for chunk, b, i in split_inline(text):
        if chunk:
            runs.append(run_xml(chunk, bold=b or bold, italic=i, size=size, color=color))
    if not runs:
        runs.append(run_xml("", size=size))
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % ("".join(props), "".join(runs))


DOCX_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr>
    <w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="맑은 고딕"/>
    <w:sz w:val="24"/><w:szCs w:val="24"/>
  </w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto" w:after="160"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Normal" w:default="1">
    <w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Body">
    <w:name w:val="Body"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:firstLine="200"/><w:jc w:val="both"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Plain">
    <w:name w:val="Plain"/><w:basedOn w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="ChapterTitle">
    <w:name w:val="Chapter Title"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="480" w:after="360"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ChapterNumber">
    <w:name w:val="Chapter Number"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="0"/></w:pPr>
    <w:rPr><w:color w:val="8A8070"/><w:sz w:val="20"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="SubTitle2">
    <w:name w:val="SubTitle2"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Quote2">
    <w:name w:val="Quote2"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:left="720" w:right="360"/></w:pPr>
    <w:rPr><w:color w:val="4A443A"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="BookTitle">
    <w:name w:val="Book Title"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="2400" w:after="240"/><w:jc w:val="center"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="72"/><w:szCs w:val="72"/></w:rPr></w:style>
</w:styles>
"""

DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>
"""

DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>
"""

DOCX_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def build_docx(meta, preface, chapters, path):
    body = []
    title = meta.get("제목", "나의 이야기")

    # 표지
    body.append(para_xml(title, style="BookTitle"))
    if meta.get("부제"):
        body.append(para_xml(meta["부제"], style="Plain", align="center", size=28))
    if meta.get("지은이"):
        body.append(para_xml("%s 지음" % meta["지은이"], style="Plain",
                             align="center", size=26, spacing_before=1200))
    if meta.get("엮은이"):
        body.append(para_xml("%s 엮음" % meta["엮은이"], style="Plain", align="center", size=22))
    if meta.get("펴낸날"):
        body.append(para_xml(meta["펴낸날"], style="Plain", align="center", size=20, color="8A8070"))

    # 머리말
    if preface:
        body.append(para_xml("머리말", style="ChapterTitle", align="center", page_break=True))
        body += blocks_to_docx(preface)

    # 차례
    if chapters:
        body.append(para_xml("차례", style="ChapterTitle", align="center", page_break=True))
        for i, (ct, _) in enumerate(chapters, 1):
            body.append(para_xml("제 %d 장   %s" % (i, ct), style="Plain"))

    # 본문
    for i, (ct, blocks) in enumerate(chapters, 1):
        body.append(para_xml("제 %d 장" % i, style="ChapterNumber",
                             align="center", page_break=True))
        body.append(para_xml(ct, style="ChapterTitle", align="center"))
        body += blocks_to_docx(blocks)

    section = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
               '<w:pgMar w:top="1985" w:right="1701" w:bottom="1985" w:left="1701"'
               ' w:header="850" w:footer="850" w:gutter="0"/></w:sectPr>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body>%s%s</w:body></w:document>" % ("".join(body), section))

    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties'
            ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
            ' xmlns:dc="http://purl.org/dc/elements/1.1/">'
            "<dc:title>%s</dc:title><dc:creator>%s</dc:creator></cp:coreProperties>"
            % (xml_escape(title), xml_escape(meta.get("지은이", ""))))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", DOCX_CONTENT_TYPES)
        z.writestr("_rels/.rels", DOCX_RELS)
        z.writestr("docProps/core.xml", core)
        z.writestr("word/_rels/document.xml.rels", DOCX_DOC_RELS)
        z.writestr("word/styles.xml", DOCX_STYLES)
        z.writestr("word/document.xml", document)


def blocks_to_docx(blocks):
    out = []
    for kind, content in blocks:
        if kind == "hr":
            out.append(para_xml("· · ·", style="Plain", align="center", color="A89E8B"))
        elif kind in ("h1", "h2"):
            out.append(para_xml(content, style="SubTitle2"))
        elif kind == "quote":
            out.append(para_xml(content, style="Quote2"))
        else:
            out.append(para_xml(content, style="Body"))
    return out


# ----------------------------------------------------------------------- PDF

def find_soffice():
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for guess in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                  r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"):
        if os.path.exists(guess):
            return guess
    return None


def find_chrome():
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome",
                 "microsoft-edge"):
        found = shutil.which(name)
        if found:
            return found
    guesses = [
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    ]
    for guess in guesses:
        if os.path.exists(guess):
            return guess
    for pattern in ("/opt/pw-browsers/chromium*/chrome-linux/chrome",):
        import glob as _glob
        hits = sorted(_glob.glob(pattern))
        if hits:
            return hits[-1]
    return None


def pdf_from_html(html_path, pdf_path):
    """크롬(또는 엣지)으로 HTML을 그대로 PDF로 인쇄합니다. 한글이 가장 곱게 나옵니다."""
    chrome = find_chrome()
    if not chrome:
        return False
    try:
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", "--print-to-pdf-no-header",
             "--print-to-pdf=" + pdf_path, "file://" + os.path.abspath(html_path)],
            check=True, capture_output=True, timeout=300,
        )
    except Exception:                                          # noqa: BLE001
        return False
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000


def build_pdf(docx_path, html_path, out_dir):
    base = os.path.splitext(os.path.basename(docx_path))[0]
    pdf = os.path.join(out_dir, base + ".pdf")

    if pdf_from_html(html_path, pdf):
        return pdf, None

    soffice = find_soffice()
    if soffice:
        try:
            subprocess.run(
                [soffice, "--headless", "--norestore", "--convert-to", "pdf",
                 "--outdir", out_dir, docx_path],
                check=True, capture_output=True, timeout=300,
            )
            if os.path.exists(pdf):
                return pdf, None
        except Exception:                                      # noqa: BLE001
            pass

    return None, ("PDF는 만들지 못했습니다.\n"
                  "         HTML 파일을 웹 브라우저로 열고 [인쇄] \u2192 [PDF로 저장] 을 "
                  "누르시면 똑같은 PDF가 만들어집니다.")


# --------------------------------------------------------------------- build

def cmd_build(argv):
    chapters_found = chapter_files()
    if not chapters_found:
        print("book/chapters/ 안에 원고가 없습니다.")
        print("'책으로 만들어 줘' 라고 말씀하시면 클로드가 답변을 원고로 옮겨 적습니다.")
        return 1

    meta, preface, chapters = load_book()
    base = safe_name(meta.get("제목", "나의 이야기"))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    html_path = os.path.join(OUTPUT_DIR, base + ".html")
    docx_path = os.path.join(OUTPUT_DIR, base + ".docx")

    build_html(meta, preface, chapters, html_path)
    build_docx(meta, preface, chapters, docx_path)
    pdf_path, pdf_note = build_pdf(docx_path, html_path, OUTPUT_DIR)

    words = sum(len(c) for _, blocks in chapters for _, c in blocks)
    print("책을 다 엮었습니다.")
    print("  제목   : %s" % meta.get("제목", ""))
    if meta.get("지은이"):
        print("  지은이 : %s" % meta["지은이"])
    print("  장 수  : %d개,  글자 수 : 약 %s자" % (len(chapters), format(words, ",")))
    print()
    print("만들어진 파일 (book/output/)")
    print("  워드 : %s" % os.path.basename(docx_path))
    print("  HTML : %s" % os.path.basename(html_path))
    if pdf_path:
        print("  PDF  : %s" % os.path.basename(pdf_path))
    else:
        print("  PDF  : %s" % pdf_note)
    return 0


# ----------------------------------------------------------------------- zip

ZIP_NAME = "자서전_시작폴더.zip"
ZIP_ROOT = "자서전_시작폴더"
ZIP_INCLUDE = [
    ".claude/skills/interview/SKILL.md",
    ".claude/skills/book-build/SKILL.md",
    "tools.py",
    "시작하기.md",
    "interview/questions.md",
    "book/meta.md",
]
ZIP_EMPTY_DIRS = ["interview/answers", "book/chapters", "book/output"]


def cmd_zip(argv):
    path = os.path.join(ROOT, ZIP_NAME)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ZIP_INCLUDE:
            src = os.path.join(ROOT, rel)
            if not os.path.exists(src):
                print("빠짐(파일 없음): %s" % rel)
                continue
            z.write(src, "%s/%s" % (ZIP_ROOT, rel))
        for rel in ZIP_EMPTY_DIRS:
            z.writestr("%s/%s/.gitkeep" % (ZIP_ROOT, rel), "")
    print("만들었습니다: %s" % ZIP_NAME)
    return 0


# ---------------------------------------------------------------------- main

COMMANDS = {
    "status": cmd_status,
    "new": cmd_new,
    "build": cmd_build,
    "zip": cmd_zip,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__.strip())
        return 0 if len(argv) < 2 else 1
    return COMMANDS[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
