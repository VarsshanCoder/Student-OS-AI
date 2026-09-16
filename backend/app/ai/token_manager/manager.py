import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.ai_tracking import AIRequest, AIUsage

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Handles context compression, quota enforcement, and usage tracking.
    """
    DEFAULT_MONTHLY_QUOTA = 100_000 # Configurable limit

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
        
    def estimate_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        return sum(self.estimate_tokens(m.get("content", "")) for m in messages if m.get("content"))

    async def check_quota(self, db: AsyncSession, user_id: str, estimated_cost: int = 0) -> bool:
        """Check if user has enough quota for the requested operation."""
        period = datetime.utcnow().strftime("%Y-%m")
        
        res = await db.execute(
            select(AIUsage)
            .where(AIUsage.user_id == user_id)
            .where(AIUsage.billing_period == period)
        )
        usage = res.scalars().first()
        
        if not usage:
            return True # No usage yet, definitely under quota
            
        if usage.total_tokens + estimated_cost > self.DEFAULT_MONTHLY_QUOTA:
            logger.warning(f"Quota exceeded for user {user_id}. {usage.total_tokens}/{self.DEFAULT_MONTHLY_QUOTA}")
            return False
            
        return True

    async def record_usage(
        self, 
        db: AsyncSession, 
        user_id: str, 
        endpoint: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int, 
        latency_ms: int,
        status: str = "success"
    ) -> None:
        """Record the AI request and aggregate token usage."""
        # 1. Create AI Request Log
        request_log = AIRequest(
            user_id=user_id,
            endpoint=endpoint,
            model_used=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status=status
        )
        db.add(request_log)
        
        # 2. Update Monthly Usage
        period = datetime.utcnow().strftime("%Y-%m")
        res = await db.execute(
            select(AIUsage)
            .where(AIUsage.user_id == user_id)
            .where(AIUsage.billing_period == period)
        )
        usage = res.scalars().first()
        
        total_used = prompt_tokens + completion_tokens
        if not usage:
            usage = AIUsage(
                user_id=user_id,
                billing_period=period,
                total_tokens=total_used,
                total_requests=1
            )
            db.add(usage)
        else:
            usage.total_tokens += total_used
            usage.total_requests += 1
            
        await db.commit()

    def enforce_input_budget(self, messages: List[Dict[str, Any]], max_context_tokens: int = 4000) -> List[Dict[str, Any]]:
        """Safely truncate history if it exceeds context windows."""
        total = self.estimate_messages_tokens(messages)
        if total <= max_context_tokens:
            return messages
            
        logger.info(f"TokenManager: Truncating from {total} to fit budget {max_context_tokens}")
        # Simplistic: keep system prompt + most recent messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        
        budget_left = max_context_tokens - self.estimate_messages_tokens(system_msgs)
        kept_msgs = []
        
        for msg in reversed(other_msgs):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            if budget_left - msg_tokens >= 0:
                kept_msgs.insert(0, msg)
                budget_left -= msg_tokens
            else:
                break
                
        return system_msgs + kept_msgs

token_manager = TokenManager()
