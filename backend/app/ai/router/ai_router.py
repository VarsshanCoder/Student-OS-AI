import logging
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import hashlib

from app.ai.schemas.routing import AIRequestParams, TaskComplexity, TaskCategory
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.token_manager.manager import token_manager
from app.ai.cache.manager import cache_manager
from app.models.ai_tracking import AICache

logger = logging.getLogger(__name__)

class AIRouter:
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {
            "groq": GroqProvider()
        }
        self.default_provider = "groq"
        
        # Model tiers
        self.models = {
            TaskComplexity.SIMPLE: "llama-3.1-8b-instant",
            TaskComplexity.MEDIUM: "mixtral-8x7b-32768",
            TaskComplexity.COMPLEX: "llama-3.3-70b-versatile"
        }
        
        # Map categories to complexity
        self.category_complexity = {
            TaskCategory.DEFINITION: TaskComplexity.SIMPLE,
            TaskCategory.SHORT_EXPLANATION: TaskComplexity.SIMPLE,
            TaskCategory.FORMATTING: TaskComplexity.SIMPLE,
            TaskCategory.SIMPLE_SUMMARY: TaskComplexity.SIMPLE,
            
            TaskCategory.STUDY_NOTES: TaskComplexity.MEDIUM,
            TaskCategory.EXPLANATION: TaskComplexity.MEDIUM,
            TaskCategory.QUIZ: TaskComplexity.MEDIUM,
            TaskCategory.STUDY_PLAN: TaskComplexity.MEDIUM,
            
            TaskCategory.MULTI_DOC_ANALYSIS: TaskComplexity.COMPLEX,
            TaskCategory.LARGE_KNOWLEDGE_BOOK: TaskComplexity.COMPLEX,
            TaskCategory.CURRICULUM_GENERATION: TaskComplexity.COMPLEX,
            TaskCategory.ADVANCED_REASONING: TaskComplexity.COMPLEX,
        }

    def _determine_complexity(self, params: AIRequestParams) -> TaskComplexity:
        if params.inferred_complexity:
            return params.inferred_complexity
            
        return self.category_complexity.get(params.task_category, TaskComplexity.MEDIUM)

    async def generate_text(self, params: AIRequestParams, db: Optional[AsyncSession] = None) -> str:
        # 1. Analyze and Normalize
        complexity = self._determine_complexity(params)
        model = params.requested_model or self.models[complexity]
        provider = self.providers[self.default_provider]
        
        # 2. Token Budgeting & Quota
        estimated_input = token_manager.estimate_messages_tokens(params.messages)
        if db:
            if not await token_manager.check_quota(db, params.user_id, estimated_input):
                raise ValueError("User quota exceeded")
            
        messages = token_manager.enforce_input_budget(params.messages)
        
        # 3. Multi-level Cache (Exact then Semantic)
        if db:
            # 3a. Exact Cache
            cached_result = await cache_manager.get_exact_match(db, params, model)
            hit_type = "exact_cache_hit"
            
            # 3b. Semantic Cache
            if not cached_result:
                cached_result = await cache_manager.get_semantic_match(db, params, model)
                if cached_result:
                    hit_type = "semantic_cache_hit"
                    
            if cached_result:
                logger.info(f"AI Cache hit ({hit_type}) for {model}")
                await token_manager.record_usage(
                    db, params.user_id, params.task_category.value, model, 
                    estimated_input, 0, 0, hit_type
                )
                return cached_result

        # 4. Execute with Retry & Fallback
        max_retries = 3
        base_delay = 1.0
        
        start_time = time.time()
        for attempt in range(max_retries):
            try:
                response = await provider.generate_text(
                    model=model, 
                    messages=messages, 
                    max_tokens=params.max_output_tokens
                )
                latency_ms = int((time.time() - start_time) * 1000)
                
                # 5. Success Tracking
                if db:
                    output_tokens = provider.get_token_count(response)
                    await token_manager.record_usage(
                        db, params.user_id, params.task_category.value, model, 
                        estimated_input, output_tokens, latency_ms, "success"
                    )
                    await cache_manager.save_to_cache(db, params, model, response)
                
                return response
                
            except Exception as e:
                logger.error(f"Provider failed on attempt {attempt+1}: {str(e)}")
                if attempt == max_retries - 1:
                    if db:
                        latency_ms = int((time.time() - start_time) * 1000)
                        await token_manager.record_usage(
                            db, params.user_id, params.task_category.value, model, 
                            estimated_input, 0, latency_ms, "failed"
                        )
                    raise e
                await asyncio.sleep(base_delay * (2 ** attempt))

    async def generate_stream(self, params: AIRequestParams, db: Optional[AsyncSession] = None) -> AsyncGenerator[Dict[str, Any], None]:
        complexity = self._determine_complexity(params)
        model = params.requested_model or self.models[complexity]
        provider = self.providers[self.default_provider]
        
        estimated_input = token_manager.estimate_messages_tokens(params.messages)
        if db:
            if not await token_manager.check_quota(db, params.user_id, estimated_input):
                yield {"type": "error", "content": "Quota exceeded"}
                return
            
        messages = token_manager.enforce_input_budget(params.messages)
        start_time = time.time()
        
        generated_text = ""
        success = False
        
        try:
            stream = provider.generate_stream(model=model, messages=messages, max_tokens=params.max_output_tokens)
            async for chunk in stream:
                if chunk["type"] == "text":
                    generated_text += chunk["content"]
                yield chunk
            success = True
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield {"type": "error", "content": f"AI service error: {e}"}
            
        if db:
            latency_ms = int((time.time() - start_time) * 1000)
            output_tokens = provider.get_token_count(generated_text)
            status = "success" if success else "failed"
            await token_manager.record_usage(
                db, params.user_id, params.task_category.value, model, 
                estimated_input, output_tokens, latency_ms, status
            )

ai_router = AIRouter()
