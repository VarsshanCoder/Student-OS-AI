import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.note import Note, NoteBlock, NoteSource
from app.models.subject import Subject
from app.worker.manager import job_manager

logger = logging.getLogger(__name__)

async def process_note_generation_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    from app.services.notes_pipeline.pipeline_orchestrator import generate_full_enterprise_note
    from app.services.notes_pipeline.tiptap_converter import convert_markdown_to_tiptap_json
    
    topic = parameters.get("topic")
    subject_name = parameters.get("subject_name", "")
    language = parameters.get("language", "en")
    source_text = parameters.get("source_text", "")
    source_type = parameters.get("source_type", "ai-generated")
    source_url = parameters.get("source_url")
    user_id = parameters.get("user_id")
    
    await job_manager.update_job(db, job_id, status="generating", progress=10, message="Generating study note content...")
    
    # We call the synchronous/blocking pipeline orchestrator.
    # In a fully optimized app this would be inside a thread pool, but for now we just yield where possible.
    # We can wrap it in asyncio.to_thread if it's strictly blocking, assuming groq/llama calls are sync.
    # Let's import asyncio to do exactly that to prevent event loop blocking.
    import asyncio
    pipeline_res = await asyncio.to_thread(
        generate_full_enterprise_note,
        topic=topic,
        subject_name=subject_name,
        language=language,
        source_text=source_text
    )
    
    await job_manager.update_job(db, job_id, status="processing", progress=80, message="Formatting note blocks...")

    blueprint = pipeline_res["blueprint"]
    full_content = pipeline_res["full_markdown"]
    tiptap_doc = pipeline_res.get("tiptap_json") or convert_markdown_to_tiptap_json(full_content, blueprint.title)
    db_blocks = pipeline_res["db_blocks"]

    subject_id = None
    if subject_name:
        res_subj = await db.execute(
            select(Subject)
            .where(Subject.user_id == user_id)
            .where(Subject.name.ilike(f"%{subject_name}%"))
        )
        subj_obj = res_subj.scalars().first()
        if subj_obj:
            subject_id = subj_obj.id

    word_count = len(full_content.split())

    note = Note(
        user_id=user_id,
        subject_id=subject_id,
        title=blueprint.title,
        content=full_content,
        tiptap_json=tiptap_doc,
        plain_text=full_content[:500],
        source="ai-generated",
        tags=blueprint.tags or [topic.lower(), "ai-generated"],
        topic=topic,
        word_count=word_count,
        icon="📝",
        estimated_reading_time=blueprint.estimated_reading_time,
        difficulty_level=blueprint.difficulty
    )

    db.add(note)
    await db.flush()

    source = NoteSource(
        note_id=note.id,
        source_type=source_type,
        url=source_url,
        metadata_json={"source_text": bool(source_text)}
    )
    db.add(source)

    for b_data in db_blocks:
        block = NoteBlock(
            note_id=note.id,
            block_type=b_data["block_type"],
            content=b_data["content"],
            order=b_data["order"]
        )
        db.add(block)

    await db.commit()

    await job_manager.update_job(
        db, job_id, 
        status="completed", 
        progress=100, 
        message="Note generated successfully.",
        result={"note_id": note.id}
    )
