"""Speech-to-text and text-to-speech via OpenAI (MediEase merge)."""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from app.config import (
    OPENAI_STT_MODEL,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
    TEMP_DIR,
    require_openai_key,
)


def _client() -> OpenAI:
    return OpenAI(api_key=require_openai_key())


def transcribe_audio(audio_path: str | Path, language: str = "en") -> str:
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    with path.open("rb") as audio_file:
        result = _client().audio.transcriptions.create(
            model=OPENAI_STT_MODEL,
            file=audio_file,
            language=language,
        )
    text = (getattr(result, "text", None) or str(result)).strip()
    if not text:
        raise ValueError("Could not transcribe audio. Please try again.")
    return text


def synthesize_speech(text: str, output_path: str | Path | None = None) -> Path:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Cannot synthesize empty text.")

    out = Path(output_path) if output_path else TEMP_DIR / "final.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Prefer gpt-4o-mini-tts; fall back to tts-1 if the account rejects it.
    try:
        response = _client().audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=cleaned[:4000],
        )
    except Exception:
        response = _client().audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=cleaned[:4000],
        )

    response.stream_to_file(str(out))
    return out
