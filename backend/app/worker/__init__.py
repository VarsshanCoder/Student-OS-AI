from .manager import job_manager
from .handlers.document_handler import process_pdf_job
from .handlers.note_handler import process_note_generation_job
from .handlers.misc_handlers import process_embedding_generation_job
from .handlers.book_handler import process_knowledge_book_job, process_chapter_retry_job

def register_all_handlers():
    job_manager.register_handler("pdf_processing", process_pdf_job)
    job_manager.register_handler("large_note_generation", process_note_generation_job)
    job_manager.register_handler("embedding_generation", process_embedding_generation_job)
    job_manager.register_handler("knowledge_book", process_knowledge_book_job)
    job_manager.register_handler("knowledge_chapter_retry", process_chapter_retry_job)
