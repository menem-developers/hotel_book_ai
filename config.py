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
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://sanjeevsanju929:sansj%40admin@cluster0.a1bur.mongodb.net/?compressors=zlib")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "hotel_booking")

    # Ollama Settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "45.0"))

settings = Settings()
