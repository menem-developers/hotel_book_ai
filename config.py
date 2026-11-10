import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Hotel Booking AI Assistant")
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # MongoDB Settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://sanjeevsanju929:sansjadmin123@cluster0.a1bur.mongodb.net/?compressors=zlib")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "hotel_booking")

    # Ollama Settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "45.0"))

    # SerpApi Settings (Real-Time Hotel Details & Google Reviews)
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "4cefc24c4e2d0e0e05a1091244f3a591e262dc75a6bbd25fe9712afd6205e8c8")
    SERPAPI_BASE_URL: str = os.getenv("SERPAPI_BASE_URL", "https://serpapi.com/search.json")

    # Voice / Natural Neural TTS Settings
    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-US-AriaNeural")

settings = Settings()
