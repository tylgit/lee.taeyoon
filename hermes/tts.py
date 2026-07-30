"""한국어 TTS 모듈.

edge-tts(마이크로소프트 에지 음성)를 사용해 자연스러운 한국어 음성을 만들고,
텔레그램 음성메시지 형식(OGG/Opus)으로 변환합니다.
ffmpeg이 없으면 MP3 파일을 그대로 반환합니다.
"""

import asyncio
import re
import shutil
import tempfile
from pathlib import Path

import edge_tts

# 시니어 분들이 듣기 편한 차분한 여성 목소리. (남성 목소리: ko-KR-InJoonNeural)
DEFAULT_VOICE = "ko-KR-SunHiNeural"
# 살짝 느리게 말해서 듣기 편하게.
DEFAULT_RATE = "-5%"

# TTS로 읽기에 너무 긴 답변은 앞부분만 읽어 줍니다.
MAX_TTS_CHARS = 1500


def clean_for_speech(text: str) -> str:
    """마크다운 표·기호 등 소리 내어 읽기 어려운 부분을 정리합니다."""
    # 코드 블록 제거
    text = re.sub(r"```.*?```", " 코드 예시는 화면의 글을 참고해 주세요. ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 표(|로 구분된 줄) 제거
    text = "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("|") and not re.fullmatch(r"[\s\-:|]+", line or " ")
    )
    # 마크다운 강조/제목/링크 기호 제거
    text = re.sub(r"[*_#>]+", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 이모지 등 특수문자 정리
    text = re.sub(r"[☀-➿\U0001F000-\U0001FAFF]", " ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()

    if len(text) > MAX_TTS_CHARS:
        cut = text[:MAX_TTS_CHARS]
        # 문장 중간에서 끊기지 않게 마지막 마침표까지만
        last_period = max(cut.rfind("."), cut.rfind("다."), cut.rfind("요."))
        if last_period > 200:
            cut = cut[: last_period + 1]
        text = cut + " 자세한 내용은 화면의 글을 확인해 주세요."
    return text


async def synthesize(text: str, voice: str = DEFAULT_VOICE) -> Path:
    """텍스트를 음성 파일로 변환합니다.

    ffmpeg이 있으면 텔레그램 음성메시지용 OGG/Opus(.ogg)를,
    없으면 MP3(.mp3)를 반환합니다.
    """
    speech_text = clean_for_speech(text)
    if not speech_text:
        raise ValueError("읽을 내용이 없습니다.")

    tmpdir = Path(tempfile.mkdtemp(prefix="hermes_tts_"))
    mp3_path = tmpdir / "answer.mp3"

    communicate = edge_tts.Communicate(speech_text, voice, rate=DEFAULT_RATE)
    await communicate.save(str(mp3_path))

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return mp3_path

    ogg_path = tmpdir / "answer.ogg"
    proc = await asyncio.create_subprocess_exec(
        ffmpeg, "-y", "-i", str(mp3_path),
        "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1",
        str(ogg_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode == 0 and ogg_path.exists():
        return ogg_path
    return mp3_path
