from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DocumentResponse(BaseModel):
    id: str
    subject_id: Optional[str] = None
    filename: str
    file_path: Optional[str] = None
    file_size: str
    page_count: int
    status: str
    content_hash: Optional[str] = None
    version: int
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    page_count: int
    job_id: Optional[str] = None

class PDFChatRequest(BaseModel):
    question: str
    language: Optional[str] = "en"

class PDFGenerateNoteRequest(BaseModel):
    topic_or_instructions: Optional[str] = None
    language: Optional[str] = "en"
