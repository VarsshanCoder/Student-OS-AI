import logging
import os
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from groq import AsyncGroq
from app.ai.providers.base import BaseAIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqProvider(BaseAIProvider):
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        
    @property
    def provider_name(self) -> str:
        return "groq"
        
    @property
    def supported_models(self) -> List[str]:
        return [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768"
        ]

    async def generate_text(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        max_tokens: Optional[int] = None,
        timeout: float = 30.0
    ) -> str:
        if not self.client:
            raise ValueError("Groq API key not configured")
            
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": timeout
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        res = await self.client.chat.completions.create(**kwargs)
        if res.choices and res.choices[0].message.content:
            return res.choices[0].message.content.strip()
        return ""

    async def generate_stream(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        max_tokens: Optional[int] = None,
        timeout: float = 30.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.client:
            yield {"type": "error", "content": "ScholarOS AI is running in mock mode. Add GROQ_API_KEY."}
            return

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "timeout": timeout
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        response_stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"type": "text", "content": chunk.choices[0].delta.content}

    def get_token_count(self, text: str, model: str = "") -> int:
        # A simple approximation: 1 token ~= 4 chars for English
        return len(text) // 4
