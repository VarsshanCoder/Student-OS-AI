import abc
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.ai.schemas.routing import AIRequestParams

class BaseAIProvider(abc.ABC):
    """Abstract base class for all AI providers to ensure no hardcoded dependencies."""
    
    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        pass
        
    @property
    @abc.abstractmethod
    def supported_models(self) -> List[str]:
        pass

    @abc.abstractmethod
    async def generate_text(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        max_tokens: Optional[int] = None,
        timeout: float = 30.0
    ) -> str:
        """Generate a single text response."""
        pass

    @abc.abstractmethod
    async def generate_stream(
        self, 
        model: str, 
        messages: List[Dict[str, Any]], 
        max_tokens: Optional[int] = None,
        timeout: float = 30.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate a streaming text response."""
        pass
        
    @abc.abstractmethod
    def get_token_count(self, text: str, model: str = "") -> int:
        """Estimate token count for the given text."""
        pass
