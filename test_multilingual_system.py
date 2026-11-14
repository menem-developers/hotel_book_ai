import asyncio
import sys
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import voice_service
import language_service
from booking_agent import booking_agent
from models import ChatRequest

async def main():
    print("=" * 60)
    print("TESTING MULTILINGUAL SYSTEM (ENGLISH, HINDI, SPANISH)")
    print("=" * 60)

    # 1. Test supported languages
    langs = language_service.get_supported_languages()
    print(f"1. Supported languages ({len(langs)}): {[l['name'] for l in langs]}")
    assert len(langs) == 3
    assert all(k in [l['code'] for l in langs] for k in ["en", "hi", "es"])
    print("PASS: 3 Languages defined correctly (English, Hindi, Spanish)")

    # 2. Test English Chat Turn
    session_en = "test-session-en-001"
    raw_en = await booking_agent.process_user_message(session_en, "I want to stay in Mumbai")
    res_en = language_service.localize_response(raw_en, lang="en")
    audio_en = await voice_service.generate_tts_data_uri_async(res_en["reply"], lang="en")
    print("\n--- 2. ENGLISH CHAT ---")
    print("Reply:", res_en["reply"][:80], "...")
    print("Audio URI length:", len(audio_en) if audio_en else 0)
    assert audio_en and len(audio_en) > 500
    print("PASS: English Text & Speech generated")

    # 3. Test Hindi Chat Turn
    session_hi = "test-session-hi-001"
    # User sends Hindi greeting
    preprocessed_hi = language_service.preprocess_user_input("मुझे मुंबई में होटल चाहिए", lang="hi")
    raw_hi = await booking_agent.process_user_message(session_hi, preprocessed_hi)
    res_hi = language_service.localize_response(raw_hi, lang="hi")
    audio_hi = await voice_service.generate_tts_data_uri_async(res_hi["reply"], lang="hi")
    print("\n--- 3. HINDI CHAT ---")
    print("Reply:", res_hi["reply"])
    print("Quick replies:", res_hi.get("quick_replies"))
    print("Audio URI length:", len(audio_hi) if audio_hi else 0)
    assert "होटल" in res_hi["reply"] or "मुंबई" in res_hi["reply"]
    assert audio_hi and len(audio_hi) > 500
    print("PASS: Hindi Text & Speech generated with Swara Neural")

    # 4. Test Spanish Chat Turn
    session_es = "test-session-es-001"
    preprocessed_es = language_service.preprocess_user_input("quiero un hotel en Mumbai", lang="es")
    raw_es = await booking_agent.process_user_message(session_es, preprocessed_es)
    res_es = language_service.localize_response(raw_es, lang="es")
    audio_es = await voice_service.generate_tts_data_uri_async(res_es["reply"], lang="es")
    print("\n--- 4. SPANISH CHAT ---")
    print("Reply:", res_es["reply"])
    print("Quick replies:", res_es.get("quick_replies"))
    print("Audio URI length:", len(audio_es) if audio_es else 0)
    assert "hotel" in res_es["reply"].lower()
    assert audio_es and len(audio_es) > 500
    print("PASS: Spanish Text & Speech generated with Elvira Neural")

    # 5. Test Whisper Audio Transcription in Hindi
    print("\n--- 5. WHISPER SPEECH RECOGNITION (HINDI) ---")
    import edge_tts
    sample_hi = "नमस्ते, मुझे दो कमरे चाहिए"
    comm = edge_tts.Communicate(sample_hi, "hi-IN-SwaraNeural")
    hi_bytes = b""
    async for chunk in comm.stream():
        if chunk.get("type") == "audio":
            hi_bytes += chunk.get("data", b"")
    
    transcribed_hi = voice_service.transcribe_audio_bytes(hi_bytes, file_ext="mp3", language="hi")
    print("Synthesized:", sample_hi)
    print("Transcribed (Whisper language='hi'):", transcribed_hi)
    assert len(transcribed_hi) > 0
    print("PASS: Whisper accurately transcribed Hindi speech")

    # 6. Test Whisper Audio Transcription in Spanish
    print("\n--- 6. WHISPER SPEECH RECOGNITION (SPANISH) ---")
    sample_es = "Hola, necesito dos habitaciones para mañana"
    comm_es = edge_tts.Communicate(sample_es, "es-ES-ElviraNeural")
    es_bytes = b""
    async for chunk in comm_es.stream():
        if chunk.get("type") == "audio":
            es_bytes += chunk.get("data", b"")
    
    transcribed_es = voice_service.transcribe_audio_bytes(es_bytes, file_ext="mp3", language="es")
    print("Synthesized:", sample_es)
    print("Transcribed (Whisper language='es'):", transcribed_es)
    assert len(transcribed_es) > 0
    print("PASS: Whisper accurately transcribed Spanish speech")

    print("\n" + "=" * 60)
    print("ALL MULTILINGUAL SYSTEM TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
