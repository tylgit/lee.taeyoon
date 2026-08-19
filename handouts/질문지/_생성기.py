#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주별 질문지 6종 생성 (md + html). 질문 내용은 questions.json 확정본을 그대로 쓴다."""
import json, os

BASE = "/home/user/lee.taeyoon/autobiography/questions.json"
OUT = "/tmp/claude-0/-home-user-lee-taeyoon/109eb882-0f20-57d0-b901-fdaa0c60ea6b/scratchpad/sheets"
os.makedirs(OUT, exist_ok=True)

data = json.load(open(BASE, encoding="utf-8"))
SEC = {s["id"]: s for s in data["sections"]}

WEEKS = [
    {"no": 1, "ord": "첫째", "ids": ["A", "B"], "date": "8월 12일",
     "title": "나의 뿌리와 어린 시절",
     "handout": "첫 수업 배부",
     "next": "다음 주에는 「C. 학창 시절 / D. 청년기」 질문지를 드립니다."},
    {"no": 2, "ord": "둘째", "ids": ["C", "D"], "date": "8월 19일",
     "title": "학창 시절과 청년기",
     "handout": "2주차 배부",
     "next": "다음 주에는 「E. 만남과 결혼 / F. 자녀와 가정」 질문지를 드립니다."},
    {"no": 3, "ord": "셋째", "ids": ["E", "F"], "date": "8월 26일",
     "title": "만남과 결혼, 그리고 가정",
     "handout": "3주차 배부",
     "next": "다음 주에는 「G. 이민 / H. 일과 성취」 질문지를 드립니다."},
    {"no": 4, "ord": "넷째", "ids": ["G", "H"], "date": "9월 2일",
     "title": "이민, 그리고 내가 일군 삶",
     "handout": "4주차 배부",
     "next": "다음 주에는 「I. 신앙의 여정 / J. 시련과 회복」 질문지를 드립니다."},
    {"no": 5, "ord": "다섯째", "ids": ["I", "J"], "date": "9월 9일",
     "title": "신앙의 여정과 지나온 아픔",
     "handout": "5주차 배부",
     "next": "다음 주에는 마지막 「K. 오늘의 나 / L. 남기고 싶은 말」 질문지를 드립니다."},
    {"no": 6, "ord": "여섯째", "ids": ["K", "L"], "date": "9월 16일",
     "title": "오늘의 나, 그리고 남기고 싶은 말",
     "handout": "6주차 배부 · 마지막 묶음",
     "next": "이것으로 90개 질문이 모두 끝났습니다. 여기까지 오신 것만으로 책의 재료는 다 모였습니다."},
]

HOWTO_MD = """## 이렇게 답하십시오

- 하루에 **두세 개 질문만** 답하십시오. 다 못 해도 괜찮습니다.
- 완전한 문장이 아니어도 됩니다. **단어 몇 개, 짧은 메모, 사진 한 장, 음성 녹음** — 모두 훌륭한 답입니다.
- 기억이 안 나면 **"기억나지 않음"**이라고 적으십시오. 그것도 답입니다.
- 나에게 해당하지 않는 질문은 **"해당 없음"**이라 적고 건너뛰십시오.
- 마음이 아픈 질문은 **답하지 않아도 됩니다.** 나중에 마음이 열리면 그때 쓰셔도 됩니다.
- 배우자, 자녀, 친구와 **이야기하면서** 떠올리면 혼자보다 두 배로 나옵니다. 휴대폰 녹음을 켜 두시면 그 대화가 그대로 원고가 됩니다.

## 답을 여는 여섯 개의 열쇠

무엇을 써야 할지 막막할 때, 아래 여섯 가지 중 **한두 가지만** 떠올려도 충분합니다.

> **언제**였습니까? / **어디**였습니까? / **누구**와 함께였습니까?
> **무슨 일**이 있었습니까? / 그때 **어떤 마음**이었습니까? / 지금 돌아보면 **어떤 의미**입니까?
"""

HOWTO_HTML = """<div class="howto">
  <h2>이렇게 답하십시오</h2>
  <ul>
    <li>하루에 <b>두세 개 질문만</b> 답하십시오. 다 못 해도 괜찮습니다.</li>
    <li>완전한 문장이 아니어도 됩니다. <b>단어 몇 개, 짧은 메모, 사진 한 장, 음성 녹음</b> — 모두 훌륭한 답입니다.</li>
    <li>기억이 안 나면 <b>"기억나지 않음"</b>이라고 적으십시오. 그것도 답입니다.</li>
    <li>나에게 해당하지 않는 질문은 <b>"해당 없음"</b>이라 적고 건너뛰십시오.</li>
    <li>마음이 아픈 질문은 <b>답하지 않아도 됩니다.</b> 나중에 마음이 열리면 그때 쓰셔도 됩니다.</li>
    <li>배우자, 자녀, 친구와 <b>이야기하면서</b> 떠올리면 혼자보다 두 배로 나옵니다. 휴대폰 녹음을 켜 두시면 그 대화가 그대로 원고가 됩니다.</li>
  </ul>
</div>
<div class="keys">
  <div class="keys-t">답을 여는 여섯 개의 열쇠 — 막막할 때 이 중 한두 가지만 떠올리십시오</div>
  <div class="keys-b"><b>언제</b>였습니까? · <b>어디</b>였습니까? · <b>누구</b>와 함께였습니까?<br>
  <b>무슨 일</b>이 있었습니까? · 그때 <b>어떤 마음</b>이었습니까? · 지금 돌아보면 <b>어떤 의미</b>입니까?</div>
</div>"""

CSS = """@page { size: letter; margin: 15mm 16mm 13mm; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "NanumGothic","Nanum Gothic","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  font-size: 12.5pt; line-height: 1.5; color: #222; background: #fff; }
.head { text-align: center; border-bottom: 3px solid #1a3a5c; padding-bottom: 9px; margin-bottom: 12px; }
.head .wk { font-size: 11pt; letter-spacing: 0.18em; color: #8a7a52; margin-bottom: 5px; }
.head h1 { font-size: 19pt; color: #1a3a5c; line-height: 1.35; }
.head .sub { font-size: 11pt; color: #666; margin-top: 6px; }
.howto { border: 2px solid #b5a679; border-radius: 8px; padding: 9px 14px; margin-bottom: 9px; background: #fdfbf5; }
.howto h2 { font-size: 12.5pt; color: #1a3a5c; margin-bottom: 4px; }
.howto ul { margin-left: 1.1em; }
.howto li { font-size: 11pt; line-height: 1.45; margin: 1px 0; }
.howto b { color: #7a3b12; }
.keys { border: 2px dashed #c9971c; border-radius: 8px; padding: 8px 14px; margin-bottom: 16px; background: #fff8e6; }
.keys-t { font-size: 11pt; font-weight: 800; color: #8a5a00; margin-bottom: 3px; }
.keys-b { font-size: 11.5pt; line-height: 1.6; color: #5a4a20; }
.sec-head { margin: 22px 0 10px; padding: 9px 14px; background: #1a3a5c; color: #fff; border-radius: 8px;
  page-break-after: avoid; page-break-inside: avoid; }
.sec-head h2 { font-size: 14pt; }
.sec-head .intro { font-size: 10.5pt; color: #d8e2ec; font-style: italic; margin-top: 3px; }
.q { margin-bottom: 17px; page-break-inside: avoid; }
.q .t { font-size: 12.5pt; font-weight: 800; color: #22303c; margin-bottom: 7px; line-height: 1.45; }
.q .t .n { color: #7a3b12; }
.q .a { display: flex; align-items: flex-start; gap: 8px; }
.q .a .lb { font-size: 11pt; color: #8a8172; flex: none; line-height: 2.05em; }
.q .a .ln { flex: 1; }
.ln div { border-bottom: 1.2px solid #999; height: 2.05em; }
.foot { margin-top: 20px; border-top: 2px dashed #c9b98a; padding-top: 11px;
  text-align: center; font-size: 11pt; color: #666; line-height: 1.7; }
.foot b { color: #7a3b12; }
@media print { .q { page-break-inside: avoid; } }
"""


def md_for(w):
    L = [f"# 내 삶을 돌아보는 질문지 ({w['ord']} 묶음) — {w['title']}", "",
         f"*(샬롬대학 챗지피티 클래스 · 자서전 만들기 · {w['no']}주차 {w['date']} 배부)*", "", "---", "",
         HOWTO_MD, "---", ""]
    for sid in w["ids"]:
        s = SEC[sid]
        L.append(f"## {sid}. {s['title']}")
        L.append("")
        if s["intro"]:
            L.append(f"*{s['intro']}*")
            L.append("")
        for it in s["questions"]:
            L.append(f"**{it['n']}. {it['q']}**")
            L.append("")
            L.append("답:")
            L.append("")
        L.append("---")
        L.append("")
    L.append(f"*{w['next']}*")
    L.append("")
    L.append("*적으신 답과 옛 사진을 다음 수업에 가져오십시오. 그것이 자서전의 벽돌이 됩니다.*")
    return "\n".join(L) + "\n"


def html_for(w):
    P = [f'<meta charset="utf-8">', f'<title>질문지 {w["no"]}주차</title>', f"<style>{CSS}</style>",
         '<div class="head">',
         f'  <div class="wk">{w["no"]}주차 · {w["date"]} 배부 · {w["ord"]} 묶음</div>',
         f'  <h1>내 삶을 돌아보는 질문지 — {w["title"]}</h1>',
         f'  <div class="sub">샬롬대학 챗지피티 클래스 · 자서전 만들기</div>',
         '</div>', HOWTO_HTML]
    for sid in w["ids"]:
        s = SEC[sid]
        intro = f'<div class="intro">{s["intro"]}</div>' if s["intro"] else ""
        P.append(f'<div class="sec-head"><h2>{sid}. {s["title"]}</h2>{intro}</div>')
        for it in s["questions"]:
            lines = "".join("<div></div>" for _ in range(3))
            P.append(f'<div class="q"><div class="t"><span class="n">{it["n"]}.</span> {it["q"]}</div>'
                     f'<div class="a"><span class="lb">답</span><span class="ln">{lines}</span></div></div>')
    P.append(f'<div class="foot">{w["next"]}<br>'
             f'<b>적으신 답과 옛 사진을 다음 수업에 가져오십시오. 그것이 자서전의 벽돌이 됩니다.</b></div>')
    return "\n".join(P) + "\n"


names = []
for w in WEEKS:
    base = f"질문지_{w['no']}주차_{''.join(w['ids'])}"
    open(f"{OUT}/{base}.md", "w", encoding="utf-8").write(md_for(w))
    open(f"{OUT}/{base}.html", "w", encoding="utf-8").write(html_for(w))
    names.append(base)
print("\n".join(names))
