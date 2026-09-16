import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.database import Base
from app.models.ai_tracking import AIUsage, AIRequest, AICache
from app.models.user import User

from app.ai.schemas.routing import AIRequestParams, TaskCategory, TaskComplexity
from app.ai.router.ai_router import AIRouter
from app.ai.token_manager.manager import TokenManager

# In-memory DB for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.provider_name = "mock"
    provider.generate_text = AsyncMock(return_value="Mock response")
    provider.get_token_count = MagicMock(return_value=10)
    return provider

@pytest.fixture
def router(mock_provider):
    router = AIRouter()
    router.providers["mock"] = mock_provider
    router.default_provider = "mock"
    return router

@pytest.mark.asyncio
async def test_model_routing_logic(router):
    """Test that task categories route to correct model complexities."""
    params_simple = AIRequestParams(
        user_id="user_1",
        task_category=TaskCategory.DEFINITION,
        messages=[{"role": "user", "content": "What is ATP?"}]
    )
    assert router._determine_complexity(params_simple) == TaskComplexity.SIMPLE
    
    params_complex = AIRequestParams(
        user_id="user_1",
        task_category=TaskCategory.CURRICULUM_GENERATION,
        messages=[{"role": "user", "content": "Generate a 12-week course."}]
    )
    assert router._determine_complexity(params_complex) == TaskComplexity.COMPLEX

@pytest.mark.asyncio
async def test_quota_enforcement(router):
    """Test that users cannot exceed their monthly token quota."""
    async with TestingSessionLocal() as db:
        user = User(email="quota@test.com", password_hash="hash", full_name="Quota")
        db.add(user)
        await db.commit()
        
        manager = TokenManager()
        
        # Test 1: Under quota
        allowed = await manager.check_quota(db, user.id, 500)
        assert allowed is True
        
        # Manually max out the quota
        usage = AIUsage(user_id=user.id, billing_period=manager.check_quota.__code__.co_consts[0], total_tokens=manager.DEFAULT_MONTHLY_QUOTA + 100, total_requests=100)
        # Hack to bypass billing period dynamic generation for testing
        from datetime import datetime
        usage.billing_period = datetime.utcnow().strftime("%Y-%m")
        db.add(usage)
        await db.commit()
        
        # Test 2: Over quota
        allowed = await manager.check_quota(db, user.id, 50)
        assert allowed is False

@pytest.mark.asyncio
async def test_retry_and_fallback(router, mock_provider):
    """Test that the router retries on failure and eventually raises or succeeds."""
    async with TestingSessionLocal() as db:
        user = User(email="retry@test.com", password_hash="hash", full_name="Retry")
        db.add(user)
        await db.commit()
        
        params = AIRequestParams(
            user_id=user.id,
            task_category=TaskCategory.STUDY_NOTES,
            messages=[{"role": "user", "content": "Make notes"}]
        )
        
        # Make provider fail 2 times, then succeed
        mock_provider.generate_text.side_effect = [Exception("Fail 1"), Exception("Fail 2"), "Success!"]
        
        # To speed up test, mock asyncio.sleep
        with patch("asyncio.sleep", new_callable=AsyncMock):
            res = await router.generate_text(params, db=db)
            
        assert res == "Success!"
        assert mock_provider.generate_text.call_count == 3
        
        # Verify AI Request log was recorded as success
        db_reqs = await db.execute(select(AIRequest).where(AIRequest.user_id == user.id))
        logs = db_reqs.scalars().all()
        assert len(logs) == 1
        assert logs[0].status == "success"

@pytest.mark.asyncio
async def test_token_budget_enforcement():
    """Test that history is truncated to fit the max context token budget."""
    manager = TokenManager()
    
    # 1 token ~= 4 chars. Max budget = 10 tokens (40 chars)
    # System: 20 chars (5 tokens)
    # Msg 1: 20 chars (5 tokens)
    # Msg 2: 20 chars (5 tokens) -> Should push Msg 1 out
    messages = [
        {"role": "system", "content": "12345678901234567890"}, # 5 tokens
        {"role": "user", "content": "abcdefghijklmnopqrst"}, # 5 tokens
        {"role": "user", "content": "zyxwvutsrqponmlkjihg"}  # 5 tokens
    ]
    
    truncated = manager.enforce_input_budget(messages, max_context_tokens=10)
    
    # Expecting: system message (5) + Msg 2 (5) = 10 tokens. Msg 1 is dropped.
    assert len(truncated) == 2
    assert truncated[0]["role"] == "system"
    assert truncated[1]["content"] == "zyxwvutsrqponmlkjihg"

@pytest.mark.asyncio
async def test_cache_hit_bypasses_provider(router, mock_provider):
    """Test that cached responses are returned without calling the provider."""
    async with TestingSessionLocal() as db:
        user = User(email="cache@test.com", password_hash="hash", full_name="Cache")
        db.add(user)
        await db.commit()
        
        params = AIRequestParams(
            user_id=user.id,
            task_category=TaskCategory.DEFINITION,
            messages=[{"role": "user", "content": "What is Python?"}]
        )
        
        # First call: Should miss cache, hit provider, and save to cache
        res1 = await router.generate_text(params, db=db)
        assert res1 == "Mock response"
        assert mock_provider.generate_text.call_count == 1
        
        # Second call: Should hit cache, bypass provider
        res2 = await router.generate_text(params, db=db)
        assert res2 == "Mock response"
        assert mock_provider.generate_text.call_count == 1 # Still 1!
