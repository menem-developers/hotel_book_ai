import os
import io
import re
import base64
import tempfile
import logging
import asyncio
import concurrent.futures
from typing import Optional

logger = logging.getLogger("voice_service")

# Default female neural voice: natural, polite, realistic American English assistant
DEFAULT_TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")

_whisper_model = None

def get_whisper_model(model_name: str = "tiny"):
    """
    Load and cache Whisper model on CPU.
    Default: 'tiny' (39M parameters, fastest, lowest memory usage on CPU).
    """
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info(f"Loading Whisper '{model_name}' model on CPU...")
        _whisper_model = whisper.load_model(model_name, device="cpu")
        logger.info(f"Whisper '{model_name}' model loaded successfully.")
    return _whisper_model


def transcribe_audio_bytes(audio_bytes: bytes, file_ext: str = "webm") -> str:
    """
    Transcribe raw audio bytes using Whisper CPU model.
    Supports webm, wav, mp3, ogg, etc.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return ""

    ext = file_ext.lstrip(".") if file_ext else "webm"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = get_whisper_model("tiny")
        # fp16=False is essential for CPU inference; temperature=0.0 gives most deterministic, accurate transcription
        result = model.transcribe(
            tmp_path,
            fp16=False,
            language="en",
            temperature=0.0,
            condition_on_previous_text=False
        )
        text = (result.get("text") or "").strip()
        logger.info(f"Whisper transcribed ({len(audio_bytes)} bytes, ext={ext}) -> '{text}'")
        return text
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}", exc_info=True)
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def clean_text_for_speech(text: str) -> str:
    """
    Clean markdown formatting, emojis, bullets, and URLs from assistant text
    to produce clean, pleasant conversational speech.
    """
    if not text:
        return ""

    # 1. Strip URLs
    t = re.sub(r'https?://\S+', '', text)
    # 2. Markdown links [text](url) -> text
    t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    # 3. Strip markdown bold/italic/headers/strikethrough/backticks
    t = re.sub(r'[*_#`~]', '', t)
    # 4. Remove emojis
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u2000-\u3300]', '', t)
    # 5. Remove bullet points, numbers at start of lines, dashes
    t = re.sub(r'^[ \t]*[•\-\*\+]\s*', '', t, flags=re.MULTILINE)
    # 6. Normalize newlines to spaces or sentence separators
    lines = [line.strip() for line in t.splitlines() if line.strip()]
    cleaned = '. '.join(lines)
    cleaned = re.sub(r'\.+', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 7. Truncate if extremely long to maintain fast natural response
    if len(cleaned) > 500:
        match = re.search(r'^(.*?[.?!])\s', cleaned[:500])
        if match:
            cleaned = match.group(1)
        else:
            cleaned = cleaned[:460].rstrip() + '...'

    return cleaned


def _run_coroutine_safely(coro):
    """
    Safely execute an async coroutine from synchronous code,
    handling threads that already have a running event loop (e.g. FastAPI / Uvicorn).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()
    else:
        return asyncio.run(coro)


async def _synthesize_edge_tts_async(text: str, voice: str) -> bytes:
    """
    Synthesize natural neural speech using edge-tts (no local GPU/heavy model required).
    """
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice)
    chunks = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk.get("data", b""))
    return b"".join(chunks)


def _synthesize_gtts(text: str, lang: str = "en") -> Optional[bytes]:
    """
    Fallback synthesis using gTTS in case network/edge-tts is unavailable.
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        logger.warning(f"gTTS fallback audio generation warning: {e}")
        return None


async def generate_tts_audio_bytes_async(text: str, voice: Optional[str] = None, lang: str = "en") -> Optional[bytes]:
    """
    Asynchronously generate natural neural MP3 audio bytes.
    Defaults to realistic female voice (en-US-AriaNeural) with automatic gTTS fallback.
    """
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        cleaned = "Thank you."

    target_voice = voice or DEFAULT_TTS_VOICE

    # 1. Primary: Natural Edge Neural Voice (Female)
    try:
        audio_bytes = await _synthesize_edge_tts_async(cleaned, target_voice)
        if audio_bytes and len(audio_bytes) > 200:
            return audio_bytes
    except Exception as e:
        logger.warning(f"Edge Neural TTS failed ({e}), attempting fallback to gTTS...")

    # 2. Secondary fallback: gTTS
    try:
        return await asyncio.to_thread(_synthesize_gtts, cleaned, lang)
    except Exception as e:
        logger.error(f"TTS fallback also failed: {e}")
        return None


def generate_tts_audio_bytes(text: str, voice: Optional[str] = None, lang: str = "en") -> Optional[bytes]:
    """
    Synchronously generate MP3 audio bytes using natural female neural TTS.
    Safe to call from sync functions, scripts, or inside running event loops.
    """
    return _run_coroutine_safely(generate_tts_audio_bytes_async(text, voice=voice, lang=lang))


async def generate_tts_data_uri_async(text: str, voice: Optional[str] = None, lang: str = "en") -> Optional[str]:
    """
    Asynchronously generate a base64 data URI for instant in-browser playback:
    'data:audio/mpeg;base64,...'
    """
    audio_bytes = await generate_tts_audio_bytes_async(text, voice=voice, lang=lang)
    if audio_bytes:
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/mpeg;base64,{b64}"
    return None


def generate_tts_data_uri(text: str, voice: Optional[str] = None, lang: str = "en") -> Optional[str]:
    """
    Synchronously generate a base64 data URI for instant in-browser playback:
    'data:audio/mpeg;base64,...'
    """
    audio_bytes = generate_tts_audio_bytes(text, voice=voice, lang=lang)
    if audio_bytes:
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/mpeg;base64,{b64}"
    return None
