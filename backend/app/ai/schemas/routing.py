from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class TaskComplexity(str, Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"

class TaskCategory(str, Enum):
    # SIMPLE
    DEFINITION = "DEFINITION"
    SHORT_EXPLANATION = "SHORT_EXPLANATION"
    FORMATTING = "FORMATTING"
    SIMPLE_SUMMARY = "SIMPLE_SUMMARY"
    
    # MEDIUM
    STUDY_NOTES = "STUDY_NOTES"
    EXPLANATION = "EXPLANATION"
    QUIZ = "QUIZ"
    STUDY_PLAN = "STUDY_PLAN"
    
    # COMPLEX
    MULTI_DOC_ANALYSIS = "MULTI_DOC_ANALYSIS"
    LARGE_KNOWLEDGE_BOOK = "LARGE_KNOWLEDGE_BOOK"
    CURRICULUM_GENERATION = "CURRICULUM_GENERATION"
    ADVANCED_REASONING = "ADVANCED_REASONING"

class AIRequestParams(BaseModel):
    user_id: str
    task_category: TaskCategory
    messages: List[Dict[str, Any]]
    
    # Optional parameters explicitly configuring routing
    requested_model: Optional[str] = None
    max_output_tokens: Optional[int] = None
    require_rag: bool = False
    priority_latency: bool = False
    
    # Inferred properties (populated by router)
    inferred_complexity: Optional[TaskComplexity] = None
    estimated_input_tokens: int = 0
