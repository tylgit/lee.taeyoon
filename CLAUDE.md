# 자서전 만들기 프로젝트

이 저장소는 말로 답하는 인터뷰로 자서전을 만드는 작업장입니다. (샬롬대학 챗지피티 클래스)

## 구조

- `autobiography/questions.json` — 자서전 질문 90문 (12개 묶음 A–L). 확정본이므로 사용자 요청 없이 고치지 않는다.
- `autobiography/answers/` — 질문마다 답변 파일 하나 (`A01.md` … `L90.md`). 각 파일: 상태 / 말한 그대로(원문) / 다듬은 글 / 메모.
- `autobiography/book/meta.md` — 책 제목·지은이·머리말.
- `autobiography/book/chapters/` — 클로드가 답변을 엮어 쓴 장 원고 (책의 본문).
- `autobiography/book/output/` — 완성본 (md·html·docx·pdf).
- `autobiography/tools.py` — `init`(답변 파일 생성) · `status`(진행 상황) · `next`(다음 질문) · `build`(책 조립·변환).

## 일하는 방법

- 사용자가 인터뷰나 답변을 원하면 → `/interview` 스킬.
- 사용자가 책 완성을 원하면 → `/book-build` 스킬.
- 제1원칙: **답변에 없는 사실을 절대 지어내지 않는다.** 다듬기는 하되 창작은 하지 않는다.
- 어르신 대상: 쉬운 말, 한 번에 하나씩, 재촉하지 않기. 아픈 주제는 언제나 건너뛸 수 있다.
- 답변 파일과 장 원고는 수정할 때마다 커밋한다. 원고가 곧 재산이므로 잃어버리면 안 된다.
