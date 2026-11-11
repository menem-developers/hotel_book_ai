import os
import io
import re
import base64
import tempfile
import logging
import asyncio
import subprocess
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


def _normalize_audio_to_wav(input_path: str) -> str:
    """
    Convert browser WebM/Opus, MP4, or other formats to pristine 16kHz mono 16-bit PCM WAV.
    This fixes missing/broken WebM container duration headers and ensures Whisper's loader
    receives clean, uncorrupted PCM audio.
    """
    wav_path = input_path + ".wav"
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=15)
        if res.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
            return wav_path
        else:
            logger.debug(f"FFmpeg normalization exited with code {res.returncode}: {res.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"FFmpeg audio normalization warning: {e}")
    return input_path


def transcribe_audio_bytes(audio_bytes: bytes, file_ext: str = "webm") -> str:
    """
    Transcribe raw audio bytes using Whisper CPU model.
    Supports webm, wav, mp3, ogg, etc.
    Automatically normalizes browser WebM to 16kHz mono WAV for high speech recognition accuracy.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning(f"Transcribe received empty or tiny audio: {len(audio_bytes) if audio_bytes else 0} bytes")
        return ""

    ext = file_ext.lstrip(".") if file_ext else "webm"
    tmp_path = None
    target_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Normalize to pristine 16kHz mono WAV using ffmpeg
        target_path = _normalize_audio_to_wav(tmp_path)

        model = get_whisper_model("tiny")
        
        # Primary pass: English with tuned thresholds and initial prompt for hotel domain
        decode_opts = {
            "fp16": False,
            "language": "en",
            "temperature": (0.0, 0.2, 0.4),
            "no_speech_threshold": 0.85,
            "logprob_threshold": -1.5,
            "condition_on_previous_text": False,
            "initial_prompt": "Hotel booking reservation, rooms, guests, dates, check-in, check-out, Mumbai, Delhi, Bangalore, Goa."
        }

        result = model.transcribe(target_path, **decode_opts)
        text = (result.get("text") or "").strip()

        # If primary English pass returned empty, attempt second pass with auto-detect language
        if not text:
            logger.info("Primary English pass returned empty, attempting auto-detect language pass...")
            decode_opts["language"] = None
            decode_opts["no_speech_threshold"] = 0.90
            result = model.transcribe(target_path, **decode_opts)
            text = (result.get("text") or "").strip()

        logger.info(f"Whisper transcribed ({len(audio_bytes)} raw bytes, file={target_path}) -> '{text}'")
        return text
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}", exc_info=True)
        return ""
    finally:
        if target_path and target_path != tmp_path and os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
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
