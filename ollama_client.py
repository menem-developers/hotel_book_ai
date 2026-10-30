import httpx
import logging
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_HOST.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def is_available(self) -> bool:
        """Check if Ollama server is responsive and model is present."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    # Check if requested model or matching prefix exists
                    return any(self.model in m or m.startswith(self.model.split(":")[0]) for m in models)
        except Exception as e:
            logger.debug(f"Ollama healthcheck failed: {e}")
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.6
    ) -> str:
        """Send chat request to Ollama and return assistant message content."""
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        
        # Include conversation history (last 8 messages for speed & context)
        payload_messages.extend(messages[-8:])

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 256  # keep responses concise and conversational
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content:
                        return content
                else:
                    logger.warning(f"Ollama returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error calling Ollama chat API: {e}")

        return ""

ollama_client = OllamaClient()
