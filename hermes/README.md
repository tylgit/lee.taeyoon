# 헤르메스 (Hermes) — 텔레그램 음성 답변 봇

텔레그램으로 질문을 보내면 **글 답변 + 한국어 음성(TTS) 답변**을 함께 보내 주는 봇입니다.
화면 글씨를 읽기 어려운 시니어 분들도 답을 **귀로 들을 수 있어** 편리합니다.

답변 성격은 저장소의 `SOUL.md`(소울.엠디 — 차분한 영적 동반자형 AI 비서) 페르소나를 따릅니다.

## 작동 방식

1. 사용자가 텔레그램에서 질문을 보냅니다.
2. Claude(claude-opus-5)가 SOUL.md 페르소나로 답을 만듭니다.
3. 봇이 답을 **글**로 먼저 보내고,
4. 이어서 **음성 메시지**(edge-tts, 한국어 '선희' 목소리)로도 보내 줍니다.

## 준비물

| 항목 | 얻는 방법 |
|---|---|
| 텔레그램 봇 토큰 | 텔레그램에서 `@BotFather` 검색 → `/newbot` 으로 발급 |
| Anthropic API 키 | https://platform.claude.com 에서 발급 |
| Python 3.10 이상 | https://python.org |
| ffmpeg (선택) | 있으면 텔레그램 '음성 메시지' 형식으로 전송 (없으면 MP3 파일로 전송) |

## 설치와 실행

```bash
cd hermes
pip install -r requirements.txt

# 환경 변수 설정
export TELEGRAM_BOT_TOKEN="봇파더에서 받은 토큰"
export ANTHROPIC_API_KEY="Anthropic API 키"

python bot.py
```

## 봇 명령어

| 명령어 | 설명 |
|---|---|
| `/start` | 인사말과 사용법 안내 |
| `/new` | 대화를 처음부터 다시 시작 |
| `/voice` | 음성 답변 켜기/끄기 |

## 참고

- 대화 기록은 메모리에만 보관되어, 봇을 재시작하면 초기화됩니다.
- 긴 답변은 앞부분 약 1,500자까지만 음성으로 읽고, 나머지는 글로 확인하도록 안내합니다.
- 목소리를 바꾸려면 `tts.py`의 `DEFAULT_VOICE`를 수정하세요. (남성: `ko-KR-InJoonNeural`)
- Claude 응답에는 안전 분류기 거절 시 자동으로 대체 모델이 응답하는 서버측 폴백(`fallbacks: "default"`)이 켜져 있습니다.
