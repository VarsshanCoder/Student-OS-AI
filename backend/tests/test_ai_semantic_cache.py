import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.cache.manager import AICacheManager
from app.ai.schemas.routing import AIRequestParams, TaskCategory

@pytest.fixture
def cache_manager():
    return AICacheManager()

@pytest.mark.asyncio
async def test_semantic_cache_isolation(cache_manager):
    """
    Verify that personalized semantic cache requests include user_id filter,
    ensuring no private information leakage between students.
    """
    # Create a personalized request (has conversational history)
    params = AIRequestParams(
        user_id="user_A",
        task_category=TaskCategory.EXPLANATION,
        messages=[
            {"role": "system", "content": "You are a tutor."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi, I'm your tutor."},
            {"role": "user", "content": "Explain binary search based on my previous mistakes."}
        ]
    )
    
    # Mock DB and embedding service
    mock_db = MagicMock()
    mock_db.get_bind.return_value.engine.name = "postgresql" # Trick the manager into running semantic search
    mock_db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    
    with patch("app.ai.cache.manager.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 768
        await cache_manager.get_semantic_match(mock_db, params, model="test-model")
        
        # Verify the generated SQL enforces user isolation
        call_args = mock_db.execute.call_args
        assert call_args is not None
        
        sql_statement = str(call_args[0][0])
        sql_params = call_args[0][1]
        
        # Must include personalization flags
        assert "is_personalized = TRUE" in sql_statement
        assert "user_id = :user_id" in sql_statement
        assert sql_params["user_id"] == "user_A"

@pytest.mark.asyncio
async def test_semantic_cache_general_query(cache_manager):
    """
    Verify that general educational queries do not filter by user_id
    and explicitly require is_personalized = FALSE.
    """
    # Create a general request (no conversational history)
    params = AIRequestParams(
        user_id="user_B",
        task_category=TaskCategory.EXPLANATION,
        messages=[
            {"role": "system", "content": "You are a tutor."},
            {"role": "user", "content": "Explain binary search."}
        ]
    )
    
    # Mock DB and embedding service
    mock_db = MagicMock()
    mock_db.get_bind.return_value.engine.name = "postgresql" # Trick the manager into running semantic search
    mock_db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    
    with patch("app.ai.cache.manager.embedding_service.get_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 768
        await cache_manager.get_semantic_match(mock_db, params, model="test-model")
        
        call_args = mock_db.execute.call_args
        sql_statement = str(call_args[0][0])
        
        # Must enforce general non-personalized cache access
        assert "is_personalized = FALSE" in sql_statement
        assert "user_id = :user_id" not in sql_statement

@pytest.mark.asyncio
async def test_semantic_cache_too_short(cache_manager):
    """
    Verify that very short queries bypass semantic caching.
    """
    params = AIRequestParams(
        user_id="user_C",
        task_category=TaskCategory.EXPLANATION,
        messages=[{"role": "user", "content": "Hi"}] # 1 word
    )
    
    mock_db = MagicMock()
    mock_db.get_bind.return_value.engine.name = "postgresql"
    mock_db.execute = AsyncMock()
    
    res = await cache_manager.get_semantic_match(mock_db, params, model="test-model")
    assert res is None
    mock_db.execute.assert_not_called()
