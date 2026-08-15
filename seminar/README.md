# 고려대학교 아틀란타 교우회 AI 워크샵 · 2026년 8월 15일

세미나 자료 3종. `assets/base.css`(공통 디자인 시스템)와 `parts/figs/*.html`(인라인 SVG 도표)를
`build.py`가 각 문서에 끼워 넣어 `dist/`에 자체 완결 HTML 한 장씩을 만든다.
아티팩트는 외부 요청이 전부 차단되므로 CSS·도표·스크립트를 모두 인라인한다.

| 산출물 | 무엇 | 쓰는 때 |
|---|---|---|
| `dist/textbook.html` | **교재** — 읽는 책. 12장 + 부록 3종 | 집에서 읽기 |
| `dist/slides.html` | **슬라이드** — 35장, 좌우 화살표로 넘김 | 강의 65분 |
| `dist/workbook.html` | **워크북** — 따라 하는 책, 실습 3개 | 실습 85분 |

## 만들기

    python3 build.py

## 사실 확인

본문의 `확인` / `확인 권장` 표시는 2026-08-15 웹 검색 교차 확인 결과다.
확인이 필요한 항목은 교재 부록 C에 모아 두었다. 원본 초고에서 바로잡은 것:

- Meta Muse Code/Spark 1.2 발표일 — 8월 12일 ❌ → **8월 5일**
- DeepSeek V4-Flash 단가 — $0.14/$0.28 ❌ → **$0.0882/$0.1764**
- Perplexity 제품명 — "Perplexity Computer" ❌ → 맥용 **Personal Computer**(4월)
- Starling MX "영구 무료 오픈 표준" — 미확인. 상용 제품군으로 보임
- Qwen3 "한국어 이해 1위" — 근거 미확인

## 색

계열색은 `dataviz` 스킬의 `validate_palette.js`로 라이트·다크 두 모드 전 항목을 통과시켰다.
색을 바꾸면 반드시 다시 돌릴 것.
