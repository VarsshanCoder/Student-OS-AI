import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.ai_tracking import AICache
from app.ai.schemas.routing import AIRequestParams
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class AICacheManager:
    """
    Implements multi-level AI caching:
    1. Exact caching (deterministic hash)
    2. Semantic caching (pgvector similarity)
    """
    def __init__(self):
        # Configure thresholds
        self.semantic_similarity_threshold = 0.90
        # By default, what version of prompt structure are we using?
        self.current_prompt_version = "v1"

    def _normalize_text(self, text_str: str) -> str:
        return " ".join(text_str.strip().lower().split())

    def generate_cache_key(
        self,
        task: str,
        normalized_prompt: str,
        context_str: str,
        language: str,
        model: str,
        prompt_version: str
    ) -> str:
        """Generates a deterministic hash for exact caching."""
        payload = {
            "task": task,
            "prompt": normalized_prompt,
            "context": context_str,
            "language": language,
            "model": model,
            "prompt_version": prompt_version
        }
        payload_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    def _extract_core_prompt_and_context(self, messages: List[Dict[str, Any]]) -> Tuple[str, str, bool]:
        """
        Separates the core prompt from context and determines if it is highly personalized.
        For simplicity:
        - System instructions = context
        - Last user message = core prompt
        - Any history = personalized context
        """
        system_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
        user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
        
        context_str = "\n".join(system_msgs)
        
        # If there is conversational history, we treat it as personalized context
        is_personalized = len(messages) > 2
        
        core_prompt = user_msgs[-1] if user_msgs else ""
        return core_prompt, context_str, is_personalized

    async def get_exact_match(
        self, 
        db: AsyncSession, 
        params: AIRequestParams, 
        model: str
    ) -> Optional[str]:
        core_prompt, context_str, _ = self._extract_core_prompt_and_context(params.messages)
        normalized_prompt = self._normalize_text(core_prompt)
        language = "en" # Simplified unless passed via params
        
        cache_key = self.generate_cache_key(
            task=params.task_category.value,
            normalized_prompt=normalized_prompt,
            context_str=context_str,
            language=language,
            model=model,
            prompt_version=self.current_prompt_version
        )
        
        res = await db.execute(
            select(AICache)
            .where(AICache.cache_key == cache_key)
            .where(AICache.prompt_version == self.current_prompt_version)
        )
        cache_entry = res.scalars().first()
        if cache_entry:
            return cache_entry.response.get("text")
        return None

    async def get_semantic_match(
        self, 
        db: AsyncSession, 
        params: AIRequestParams, 
        model: str
    ) -> Optional[str]:
        """Searches for semantically equivalent cached educational queries."""
        core_prompt, _, is_personalized = self._extract_core_prompt_and_context(params.messages)
        
        if not core_prompt or len(core_prompt.split()) < 3:
            return None # Too short for meaningful semantic match

        query_vec = await embedding_service.get_embedding(core_prompt)
        
        # Only use pgvector if running on postgres (fallback handled cleanly)
        bind = db.get_bind()
        if bind.engine.name != 'postgresql':
            return None # Skip semantic cache in local sqlite testing to avoid complex JSON Euclidean ops

        # Base filter: match model and prompt_version
        # Using cosine distance <=> (smaller is better). 1 - distance = similarity.
        
        sql = """
            SELECT response, 1 - (embedding <=> :query_vec::vector) AS similarity
            FROM ai_cache
            WHERE model = :model 
              AND prompt_version = :prompt_version
              AND task_category = :task_category
        """
        
        # Privacy enforcement: if personalized, restrict to this user's cache
        sql_params = {
            "query_vec": str(query_vec),
            "model": model,
            "prompt_version": self.current_prompt_version,
            "task_category": params.task_category.value
        }
        
        if is_personalized:
            sql += " AND is_personalized = TRUE AND user_id = :user_id"
            sql_params["user_id"] = params.user_id
        else:
            # We can safely use non-personalized general answers from anyone
            sql += " AND is_personalized = FALSE"
            
        sql += " ORDER BY embedding <=> :query_vec::vector LIMIT 1"

        try:
            result = await db.execute(text(sql), sql_params)
            row = result.first()
            if row and row.similarity >= self.semantic_similarity_threshold:
                # Cache hit!
                response_json = row.response
                return response_json.get("text") if response_json else None
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            
        return None

    async def save_to_cache(
        self, 
        db: AsyncSession, 
        params: AIRequestParams, 
        model: str, 
        response_text: str
    ) -> None:
        core_prompt, context_str, is_personalized = self._extract_core_prompt_and_context(params.messages)
        normalized_prompt = self._normalize_text(core_prompt)
        language = "en"
        
        cache_key = self.generate_cache_key(
            task=params.task_category.value,
            normalized_prompt=normalized_prompt,
            context_str=context_str,
            language=language,
            model=model,
            prompt_version=self.current_prompt_version
        )
        
        # Avoid duplicate keys
        res = await db.execute(select(AICache).where(AICache.cache_key == cache_key))
        if res.scalars().first():
            return
            
        try:
            # Generate embedding for semantic cache
            embedding_vec = await embedding_service.get_embedding(core_prompt)
            
            entry = AICache(
                cache_key=cache_key,
                response={"text": response_text},
                model=model,
                prompt_version=self.current_prompt_version,
                task_category=params.task_category.value,
                normalized_prompt=normalized_prompt,
                embedding=embedding_vec,
                is_personalized=is_personalized,
                user_id=params.user_id if is_personalized else None
            )
            db.add(entry)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning(f"Failed to save to AI multi-level cache: {e}")

cache_manager = AICacheManager()
