import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AIRouter:
    """
    Implements AdvanceNew.md Section 10 & 17: Model Routing.
    Routes to Fast Model vs Strong Model based on task complexity.
    """
    FAST_MODEL = "llama-3.1-8b-instant"
    STANDARD_MODEL = "mixtral-8x7b-32768"
    STRONG_MODEL = "llama-3.3-70b-versatile"

    def route_request(self, messages: List[Dict[str, str]], action: str = None) -> str:
        # Analyze complexity based on explicit action overrides
        if action in ["notes", "explain_better", "quiz", "mindmap"]:
            logger.info(f"AIRouter: Routing to STRONG_MODEL for complex action '{action}'")
            return self.STRONG_MODEL
        
        last_msg = messages[-1].get("content", "") if messages else ""
        words = len(last_msg.split())
        
        # Simple definition or factual lookup
        if words < 15 and any(keyword in last_msg.lower() for keyword in ["what is", "define", "who is", "when"]):
            logger.info("AIRouter: Routing to FAST_MODEL for simple lookup query")
            return self.FAST_MODEL
            
        if "summarize" in last_msg.lower() or action == "summarize":
            logger.info("AIRouter: Routing to FAST_MODEL for summarization task")
            return self.FAST_MODEL

        # Default fallback for medium/standard academic queries
        logger.info("AIRouter: Routing to STANDARD_MODEL/STRONG_MODEL fallback")
        return self.STRONG_MODEL

ai_router = AIRouter()
