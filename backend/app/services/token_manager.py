import logging
from typing import List, Dict
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Implements AdvanceNew.md Sections 11, 12, 13: 
    Token Manager and Rolling Conversation Summaries for Context Compression.
    """
    def __init__(self, max_context_tokens: int = 2500):
        # We set a strict budget for history to leave room for RAG and generation output
        self.max_context_tokens = max_context_tokens
        self.chars_per_token = 4

    def estimate_tokens(self, text: str) -> int:
        return len(text) // self.chars_per_token

    async def compress_conversation(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        total_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages if m.get("content"))
        
        if total_tokens <= self.max_context_tokens:
            return messages # Under budget, no compression needed
            
        logger.info(f"TokenManager: Conversation exceeds token budget ({total_tokens} > {self.max_context_tokens}). Compressing...")
        
        # Keep the most recent context intact (last 4 messages: e.g., assistant, user, assistant, user)
        recent_messages = messages[-4:]
        old_messages = messages[:-4]
        
        if not old_messages:
            return recent_messages
            
        # Summarize older messages to save tokens
        old_text = "\n".join([f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}" for m in old_messages])
        prompt = (
            "Summarize the following academic conversation concisely. "
            "Capture the student's current understanding, the core topic discussed, and any goals. "
            "Do NOT include conversational filler.\n\n"
            f"CONVERSATION:\n{old_text}"
        )
        
        try:
            summary = await ai_service.generate_text_single(prompt)
            if summary:
                compressed_history = [
                    {"role": "system", "content": f"CONVERSATION SUMMARY OF PAST MESSAGES:\n{summary}"}
                ] + recent_messages
                logger.info(f"TokenManager: Successfully compressed {len(old_messages)} messages into a summary.")
                return compressed_history
        except Exception as e:
            logger.warning(f"TokenManager: Compression failed, truncating safely instead: {e}")
            
        # Fallback: strict truncation if summary generation fails
        return messages[-6:]

token_manager = TokenManager()
