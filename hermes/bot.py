"""헤르메스(Hermes) — 텔레그램 음성 답변 봇.

텔레그램으로 질문을 보내면 Google Gemini(무료 등급)가 답하고, 답변을
글과 함께 한국어 음성(TTS)으로도 보내 줍니다. 시니어 사용자를 위해
SOUL.md(소울.엠디) 페르소나로 차분하고 쉽게 설명합니다.

실행 전 필요한 환경 변수:
  TELEGRAM_BOT_TOKEN  텔레그램 봇 토큰 (@BotFather 에서 발급)
  GEMINI_API_KEY      Google AI Studio에서 무료 발급 (https://aistudio.google.com)
"""

import asyncio
import logging
import os
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import tts

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO
)
logger = logging.getLogger("hermes")

MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 2048
MAX_HISTORY_TURNS = 20          # 대화 기억 길이(사용자+봇 합산 메시지 수)
TELEGRAM_MSG_LIMIT = 4000       # 텔레그램 메시지 길이 제한(4096)보다 여유 있게

SOUL_PATH = Path(__file__).resolve().parent.parent / "SOUL.md"

VOICE_GUIDE = (
    "\n\n---\n\n"
    "## 음성 답변 안내\n"
    "당신의 답변은 글과 함께 음성(TTS)으로도 재생됩니다. "
    "소리 내어 읽었을 때 자연스럽도록 문장을 짧고 명확하게 쓰고, "
    "표는 꼭 필요할 때만 사용하십시오. 특수기호와 이모지는 최소화하십시오."
)


def load_system_prompt() -> str:
    try:
        return SOUL_PATH.read_text(encoding="utf-8") + VOICE_GUIDE
    except OSError:
        logger.warning("SOUL.md를 찾지 못해 기본 페르소나로 시작합니다.")
        return (
            "당신은 시니어 사용자를 돕는 차분하고 친절한 한국어 AI 비서입니다. "
            "존댓말을 쓰고, 쉽고 짧은 문장으로 핵심부터 설명하십시오." + VOICE_GUIDE
        )


SYSTEM_PROMPT = load_system_prompt()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

GEN_CONFIG = genai_types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)

# 채팅방별 대화 기록 (메모리 보관 — 봇을 재시작하면 초기화됩니다)
histories: dict[int, list[genai_types.Content]] = {}


def ask_gemini(chat_id: int, question: str) -> str:
    """대화 기록을 이어서 Gemini에게 질문하고 답변 텍스트를 돌려줍니다."""
    history = histories.setdefault(chat_id, [])
    history.append(
        genai_types.Content(role="user", parts=[genai_types.Part(text=question)])
    )

    response = client.models.generate_content(
        model=MODEL, contents=history, config=GEN_CONFIG
    )

    answer = (response.text or "").strip()
    if not answer:
        history.pop()
        return (
            "죄송합니다. 이 질문에는 답변을 만들지 못했습니다. "
            "표현을 조금 바꿔서 다시 질문해 주시겠어요?"
        )

    history.append(
        genai_types.Content(role="model", parts=[genai_types.Part(text=answer)])
    )
    # 오래된 대화는 잘라내어 무료 사용량과 속도를 관리합니다.
    if len(history) > MAX_HISTORY_TURNS:
        del history[: len(history) - MAX_HISTORY_TURNS]
    return answer


def split_message(text: str, limit: int = TELEGRAM_MSG_LIMIT) -> list[str]:
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    parts.append(text)
    return parts


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    context.chat_data["voice_on"] = True
    await update.message.reply_text(
        "안녕하세요. 저는 헤르메스입니다.\n\n"
        "궁금한 것을 글로 보내 주시면, 답을 글과 음성으로 함께 보내 드립니다.\n"
        "음성만 듣고 싶지 않으시면 /voice 를 눌러 끄고 켤 수 있습니다.\n"
        "대화를 처음부터 다시 시작하려면 /new 를 눌러 주세요."
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("새 대화를 시작합니다. 무엇이 궁금하신가요?")


async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice_on = not context.chat_data.get("voice_on", True)
    context.chat_data["voice_on"] = voice_on
    if voice_on:
        await update.message.reply_text("음성 답변을 켰습니다. 🔊")
    else:
        await update.message.reply_text("음성 답변을 껐습니다. 글로만 답해 드립니다.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    question = (update.message.text or "").strip()
    if not question:
        return

    await chat.send_action(ChatAction.TYPING)
    try:
        # API 호출이 봇 전체를 멈추지 않도록 별도 스레드에서 실행합니다.
        answer = await asyncio.to_thread(ask_gemini, chat.id, question)
    except genai_errors.APIError as e:
        logger.error("Gemini API 오류: %s", e)
        if e.code == 429:
            await update.message.reply_text(
                "오늘 무료 사용량을 잠시 넘었습니다. 1분쯤 뒤에 다시 질문해 주세요."
            )
        else:
            await update.message.reply_text(
                "답변 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요."
            )
        return
    except Exception:
        logger.exception("알 수 없는 오류")
        await update.message.reply_text(
            "인터넷 연결에 문제가 있는 것 같습니다. 잠시 후 다시 시도해 주세요."
        )
        return

    # 1) 글 답변
    for part in split_message(answer):
        await update.message.reply_text(part)

    # 2) 음성 답변
    if not context.chat_data.get("voice_on", True):
        return
    try:
        await chat.send_action(ChatAction.RECORD_VOICE)
        audio_path = await tts.synthesize(answer)
        with open(audio_path, "rb") as f:
            if audio_path.suffix == ".ogg":
                await update.message.reply_voice(voice=f)
            else:
                await update.message.reply_audio(audio=f, title="헤르메스 답변")
    except Exception:
        logger.exception("TTS 변환 실패")
        await update.message.reply_text("(음성 변환에 실패해서 글로만 답변드렸습니다.)")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN 환경 변수를 설정해 주세요.")
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            "GEMINI_API_KEY 환경 변수를 설정해 주세요.\n"
            "https://aistudio.google.com 에서 구글 계정으로 무료 발급받을 수 있습니다."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("헤르메스 봇을 시작합니다. (모델: %s)", MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
