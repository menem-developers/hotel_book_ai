import os
import io
import re
import base64
import tempfile
import logging
from typing import Optional

logger = logging.getLogger("voice_service")

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
        # fp16=False is essential for CPU inference
        result = model.transcribe(tmp_path, fp16=False, language="en")
        text = (result.get("text") or "").strip()
        logger.info(f"Whisper transcribed ({len(audio_bytes)} bytes) -> '{text}'")
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
    # 3. Strip bold, italic, headings, backticks, code markers
    t = re.sub(r'[*_#`~]', '', t)
    # 4. Remove emojis
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u2000-\u3300]', '', t)
    # 5. Remove bullet points and list dashes
    t = re.sub(r'^[ \t]*[•\-\*\+]\s*', '', t, flags=re.MULTILINE)
    # 6. Normalize newlines to spaces or sentence separators
    lines = [line.strip() for line in t.splitlines() if line.strip()]
    cleaned = '. '.join(lines)
    cleaned = re.sub(r'\.+', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 7. Truncate if very long for comfortable speech playback
    if len(cleaned) > 360:
        match = re.search(r'^(.*?[.?!])\s', cleaned[:360])
        if match:
            cleaned = match.group(1)
        else:
            cleaned = cleaned[:330] + '...'

    return cleaned


def generate_tts_audio_bytes(text: str, lang: str = "en") -> Optional[bytes]:
    """
    Generate MP3 audio bytes using gTTS.
    """
    cleaned = clean_text_for_speech(text)
    if not cleaned:
        cleaned = "Thank you."

    try:
        from gtts import gTTS
        tts = gTTS(text=cleaned, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        logger.warning(f"gTTS audio generation warning: {e}")
        return None


def generate_tts_data_uri(text: str, lang: str = "en") -> Optional[str]:
    """
    Generate a base64 data URI for instant in-browser playback:
    'data:audio/mpeg;base64,...'
    """
    audio_bytes = generate_tts_audio_bytes(text, lang=lang)
    if audio_bytes:
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/mpeg;base64,{b64}"
    return None
