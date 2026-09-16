import os
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio

from app.models.knowledge_book import KnowledgeBook, KnowledgeChapter
from app.worker.manager import job_manager
from app.services.book_pipeline.prompts import generate_outline, generate_chapter_content
from app.services.book_pipeline.pdf_generator import convert_markdown_to_pdf

logger = logging.getLogger(__name__)

async def process_knowledge_book_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    """Main workflow to generate a Knowledge Book."""
    book_id = parameters.get("book_id")
    if not book_id:
        raise ValueError("Missing book_id")
        
    res = await db.execute(select(KnowledgeBook).where(KnowledgeBook.id == book_id))
    book = res.scalar_one_or_none()
    if not book:
        raise ValueError("Knowledge Book not found")
        
    try:
        # Step 1: Outline
        if book.status in ["queued", "outlining"]:
            await job_manager.update_job(db, job_id, status="outlining", progress=5, message="Generating book outline...")
            book.status = "outlining"
            await db.commit()
            
            outline_data = await generate_outline(
                topic=book.topic,
                level=book.level,
                language=book.language,
                style=book.style,
                target_length=book.target_length,
                syllabus=parameters.get("syllabus", "")
            )
            
            book.outline_json = outline_data
            
            # Create chapters
            chapters = outline_data.get("chapters", [])
            book.target_chapters = len(chapters)
            
            for ch_data in chapters:
                ch = KnowledgeChapter(
                    book_id=book.id,
                    title=ch_data.get("title", "Untitled Chapter"),
                    order=ch_data.get("order", 0),
                    status="pending",
                    outline_json=ch_data
                )
                db.add(ch)
            
            book.status = "generating_chapters"
            await db.commit()
            await db.refresh(book)

        # Step 2: Generate Chapters
        if book.status == "generating_chapters":
            res = await db.execute(
                select(KnowledgeChapter)
                .where(KnowledgeChapter.book_id == book.id)
                .order_by(KnowledgeChapter.order)
            )
            chapters = res.scalars().all()
            total_chapters = len(chapters)
            
            for idx, ch in enumerate(chapters):
                if ch.status == "completed":
                    continue
                    
                msg = f"Generating chapter {idx+1}/{total_chapters}: {ch.title}"
                prog = 10 + int((idx / total_chapters) * 70)
                await job_manager.update_job(db, job_id, status="generating_chapters", progress=prog, message=msg)
                
                ch.status = "generating"
                await db.commit()
                
                try:
                    content = await generate_chapter_content(
                        topic=book.topic,
                        chapter_title=ch.title,
                        objectives=ch.outline_json.get("learning_objectives", []),
                        sections=ch.outline_json.get("sections", []),
                        style=book.style,
                        language=book.language
                    )
                    
                    # Validation: Check if it's missing sections or broken
                    if len(content) < 100:
                        raise ValueError("Generated content is suspiciously short.")
                        
                    ch.content = content
                    ch.status = "completed"
                    ch.error_message = None
                except Exception as e:
                    ch.status = "failed"
                    ch.error_message = str(e)
                    logger.error(f"Failed to generate chapter {ch.id}: {e}")
                    
                await db.commit()
            
            # Check if all completed
            failed = [c for c in chapters if c.status == "failed"]
            if failed:
                book.status = "failed"
                await db.commit()
                raise ValueError(f"{len(failed)} chapters failed to generate. Please retry them individually.")
            
            book.status = "assembling"
            await db.commit()

        # Step 3: Assembly & PDF
        if book.status == "assembling":
            await job_manager.update_job(db, job_id, status="assembling", progress=85, message="Assembling final document...")
            
            res = await db.execute(
                select(KnowledgeChapter)
                .where(KnowledgeChapter.book_id == book.id)
                .order_by(KnowledgeChapter.order)
            )
            chapters = res.scalars().all()
            
            full_md = f"# {book.title}\n\n"
            for ch in chapters:
                full_md += f"{ch.content}\n\n---\n\n"
                
            os.makedirs("uploads/books", exist_ok=True)
            md_path = f"uploads/books/{book.id}.md"
            pdf_path = f"uploads/books/{book.id}.pdf"
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_md)
                
            book.markdown_path = md_path
            await db.commit()
            
            await job_manager.update_job(db, job_id, status="assembling", progress=90, message="Rendering PDF deterministically...")
            
            # Convert to PDF
            success = await asyncio.to_thread(convert_markdown_to_pdf, full_md, pdf_path)
            if success:
                book.pdf_path = pdf_path
            
            book.status = "indexing"
            await db.commit()

        # Step 4: Index into RAG
        if book.status == "indexing":
            await job_manager.update_job(db, job_id, status="indexing", progress=95, message="Indexing into RAG system...")
            
            if book.pdf_path:
                from app.rag.orchestrator import rag_orchestrator
                # Create a background job to RAG index this generated PDF
                # (Re-use existing RAG logic, but simplified)
                try:
                    with open(book.pdf_path, "rb") as f:
                        file_bytes = f.read()
                    await rag_orchestrator.process_document(
                        db=db,
                        user_id=book.user_id,
                        filename=f"{book.topic}_Book.pdf",
                        file_bytes=file_bytes
                    )
                except Exception as rag_e:
                    logger.warning(f"Failed to RAG index knowledge book: {rag_e}")
                    
            book.status = "completed"
            book.progress = 100
            await db.commit()
            
        await job_manager.update_job(db, job_id, status="completed", progress=100, message="Knowledge book generated successfully!")

    except Exception as e:
        book.status = "failed"
        await db.commit()
        raise e

async def process_chapter_retry_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    """Job to retry a single chapter."""
    chapter_id = parameters.get("chapter_id")
    book_id = parameters.get("book_id")
    
    res = await db.execute(select(KnowledgeChapter).where(KnowledgeChapter.id == chapter_id))
    ch = res.scalar_one_or_none()
    if not ch: raise ValueError("Chapter not found")
    
    res_b = await db.execute(select(KnowledgeBook).where(KnowledgeBook.id == book_id))
    book = res_b.scalar_one()
    
    ch.status = "generating"
    await db.commit()
    
    try:
        content = await generate_chapter_content(
            topic=book.topic,
            chapter_title=ch.title,
            objectives=ch.outline_json.get("learning_objectives", []),
            sections=ch.outline_json.get("sections", []),
            style=book.style,
            language=book.language
        )
        ch.content = content
        ch.status = "completed"
        ch.error_message = None
        await db.commit()
        
        # Check if the whole book can proceed
        res_all = await db.execute(select(KnowledgeChapter).where(KnowledgeChapter.book_id == book.id))
        all_chs = res_all.scalars().all()
        if all(c.status == "completed" for c in all_chs) and book.status == "failed":
            # Resume book job
            book.status = "assembling"
            await db.commit()
            
            await job_manager.create_job(
                db=db, user_id=book.user_id, job_type="knowledge_book",
                parameters={"book_id": book.id}
            )
            
    except Exception as e:
        ch.status = "failed"
        ch.error_message = str(e)
        await db.commit()
        raise e
        
    await job_manager.update_job(db, job_id, status="completed", progress=100)
