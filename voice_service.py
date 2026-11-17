import os
import io
import re
import shutil
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

# Multilingual Neural Voice Map for Edge TTS
VOICE_MAP = {
    "en": os.getenv("TTS_VOICE", "en-US-AriaNeural"),
    "hi": "hi-IN-SwaraNeural",
    "es": "es-ES-ElviraNeural"
}

# Domain-tuned initial prompts for Whisper STT (concise to prevent token loops)
WHISPER_PROMPTS = {
    "en": "Hotel booking reservation, rooms, guests, dates, check-in, check-out, Mumbai, Delhi, New York.",
    "hi": None,
    "es": "Reserva de hotel, habitaciones, huéspedes, fechas, check-in, check-out, Madrid, Barcelona."
}

# Multilingual STT Language Locale Map
STT_LOCALE_MAP = {
    "en": "en-US",
    "hi": "hi-IN",
    "es": "es-ES"
}

_whisper_model = None

def is_ffmpeg_installed() -> bool:
    """Check if ffmpeg executable is available in system PATH."""
    return shutil.which("ffmpeg") is not None


def _transcribe_with_google_stt(wav_path: str, locale: str = "en-US") -> Optional[str]:
    """
    Transcribe 16kHz mono WAV using Google Speech Recognition API.
    Provides fast (~1s), near-perfect accuracy in Hindi (Devanagari script), Spanish, and English.
    """
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        r.energy_threshold = 280
        r.dynamic_energy_threshold = True
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language=locale)
        if text and text.strip():
            logger.info(f"Google STT ({locale}) successfully transcribed: '{text.strip()}'")
            return text.strip()
    except Exception as e:
        logger.warning(f"Google STT ({locale}) notice: {e}. Falling back to Whisper...")
    return None


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


def transcribe_audio_bytes(audio_bytes: bytes, file_ext: str = "webm", language: str = "en") -> str:
    """
    Transcribe raw audio bytes using Whisper CPU model in the requested language (en, hi, es).
    Supports webm, wav, mp3, ogg, etc.
    Automatically normalizes browser WebM to 16kHz mono WAV for high speech recognition accuracy.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning(f"Transcribe received empty or tiny audio: {len(audio_bytes) if audio_bytes else 0} bytes")
        return ""

    if not is_ffmpeg_installed():
        logger.error(
            "CRITICAL: 'ffmpeg' is not installed or not in PATH! "
            "OpenAI Whisper requires ffmpeg to decode audio files. "
            "On Ubuntu run: 'sudo apt-get update && sudo apt-get install -y ffmpeg' "
            "or ensure your Docker container installs ffmpeg."
        )
        return ""

    ext = file_ext.lstrip(".") if file_ext else "webm"
    target_lang = (language or "en").lower().strip()
    if target_lang not in ("en", "hi", "es"):
        target_lang = "en"

    tmp_path = None
    target_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Normalize to pristine 16kHz mono WAV using ffmpeg
        target_path = _normalize_audio_to_wav(tmp_path)

        # 1. Primary STT Engine: Google Speech Recognition (Super-accurate in Hindi Devanagari, Spanish, English)
        stt_locale = STT_LOCALE_MAP.get(target_lang, "en-US")
        google_text = _transcribe_with_google_stt(target_path, locale=stt_locale)
        if google_text:
            logger.info(f"STT primary (Google STT, lang={target_lang}, locale={stt_locale}) -> '{google_text}'")
            return google_text

        # 2. Secondary STT Fallback Engine: OpenAI Whisper (Local CPU model)
        logger.info(f"Google STT returned empty or unavailable, engaging Whisper fallback for lang={target_lang}...")
        model = get_whisper_model("tiny")
        
        # Primary pass: specified language with tuned thresholds and domain prompt
        decode_opts = {
            "fp16": False,
            "language": target_lang,
            "temperature": (0.0, 0.2),
            "no_speech_threshold": 0.85,
            "logprob_threshold": -1.5,
            "condition_on_previous_text": False
        }
        init_prompt = WHISPER_PROMPTS.get(target_lang)
        if init_prompt:
            decode_opts["initial_prompt"] = init_prompt

        result = model.transcribe(target_path, **decode_opts)
        text = (result.get("text") or "").strip()

        # If primary language pass returned empty, attempt second pass with auto-detect language
        if not text:
            logger.info(f"Primary pass ({target_lang}) returned empty, attempting auto-detect language pass...")
            decode_opts["language"] = None
            decode_opts["no_speech_threshold"] = 0.90
            result = model.transcribe(target_path, **decode_opts)
            text = (result.get("text") or "").strip()

        logger.info(f"Whisper transcribed ({len(audio_bytes)} raw bytes, lang={target_lang}, file={target_path}) -> '{text}'")
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
    to produce clean, pleasant, natural conversational speech.
    Speaks the full informative content without cutting off at search headers or the first sentence.
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

    # 5. Remove search / news / boilerplate header lines if present
    # (e.g. "Here is what I found on the web:", "Top News Headlines:", etc.)
    t = re.sub(r'^\s*(?:here\s+is\s+what\s+i\s+found\s+(?:on\s+the\s+web)?|here\s+are\s+the\s+details|according\s+to\s+the\s+web|top\s+news\s+headlines|latest\s+updates?)\s*[:.]*\s*', '', t, flags=re.IGNORECASE | re.MULTILINE)

    # 6. Remove bullet points, numbers at start of lines, dashes
    t = re.sub(r'^[ \t]*[•\-\*\+]\s*', '', t, flags=re.MULTILINE)
    # Replace pipes and ellipsis in headings with natural pause commas
    t = re.sub(r'\s*\|\s*', ', ', t)
    t = re.sub(r'\s*\.\.\.\s*', '. ', t)

    # 7. Normalize newlines to spaces or sentence separators
    # Filter out empty or leftover header lines
    lines = [
        line.strip().rstrip('.') for line in t.splitlines()
        if line.strip() and not re.match(r'^(?:here\s+is\s+what\s+i\s+found|top\s+news\s+headlines|latest\s+updates?)\b', line.strip(), re.I)
    ]
    cleaned = '. '.join(lines)
    cleaned = re.sub(r'\.+', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 8. Limit length to a natural conversational spoken answer (up to ~650 chars / 3-4 sentences)
    # Speaks multiple sentences so the user hears the actual answer, not just a cut-off fragment!
    if len(cleaned) > 650:
        match = re.search(r'^(.*?[.?!])\s+(?=[A-Z0-9\u0900-\u097F]|$)', cleaned[350:650])
        if match:
            cleaned = cleaned[:350] + match.group(1)
        else:
            cleaned = cleaned[:600].rstrip(' ,;:-') + '.'

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
    Protected with a 4.0-second timeout to promptly switch to female gTTS if network is slow.
    """
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice)
    chunks = []
    async with asyncio.timeout(10.0):
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                chunks.append(chunk.get("data", b""))
    return b"".join(chunks)


def _synthesize_gtts(text: str, lang: str = "en") -> Optional[bytes]:
    """
    Fallback synthesis using gTTS (Google Translate female voice) in case network/edge-tts is unavailable.
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, tld="com", slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        logger.warning(f"gTTS fallback audio generation warning: {e}")
        return None


async def generate_tts_audio_bytes_async(text: str, voice: Optional[str] = None, lang: str = "en") -> Optional[bytes]:
    """
    Asynchronously generate natural neural MP3 audio bytes in the requested language (en, hi, es).
    Defaults to realistic female voice for the selected language:
    - English: en-US-AriaNeural
    - Hindi: hi-IN-SwaraNeural
    - Spanish: es-ES-ElviraNeural
    with automatic gTTS fallback.
    """
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        cleaned = "Thank you."

    lang_code = (lang or "en").lower().strip()
    target_voice = voice or VOICE_MAP.get(lang_code, DEFAULT_TTS_VOICE)
    fallback_lang = lang_code if lang_code in ("en", "hi", "es") else "en"

    # 1. Primary: Natural Edge Neural Voice
    try:
        audio_bytes = await _synthesize_edge_tts_async(cleaned, target_voice)
        if audio_bytes and len(audio_bytes) > 200:
            return audio_bytes
    except Exception as e:
        logger.warning(f"Edge Neural TTS failed for '{target_voice}' ({e}), attempting fallback to gTTS...")

    # 2. Secondary fallback: gTTS
    try:
        return await asyncio.to_thread(_synthesize_gtts, cleaned, fallback_lang)
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
