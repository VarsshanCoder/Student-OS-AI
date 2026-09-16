import re
from typing import List, Dict, Any

class DocumentChunker:
    """
    Splits text into semantically useful chunks preserving:
    - pages
    - paragraphs
    - headings (best effort)
    """
    def __init__(self, max_chunk_size=1000, overlap=100):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk_paginated_text(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes paginated text and chunks it while keeping track of the page origin.
        """
        chunks = []
        chunk_index = 0
        
        for page in pages:
            page_num = page["page_number"]
            text = page["text"]
            
            # Simple boundary preservation: Split by double newline (paragraphs)
            paragraphs = re.split(r'\n\s*\n', text)
            
            current_chunk_text = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                if len(current_chunk_text) + len(para) > self.max_chunk_size and current_chunk_text:
                    # Finalize current chunk
                    chunks.append({
                        "chunk_index": chunk_index,
                        "page_number": page_num,
                        "content": current_chunk_text.strip()
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_text = current_chunk_text[-self.overlap:] if self.overlap > 0 else ""
                    # Don't overlap mid-word
                    if " " in overlap_text:
                        overlap_text = overlap_text.split(" ", 1)[-1]
                    current_chunk_text = overlap_text + "\n\n" + para
                else:
                    if current_chunk_text:
                        current_chunk_text += "\n\n"
                    current_chunk_text += para
            
            # Flush remainder of the page
            if current_chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                    "content": current_chunk_text.strip()
                })
                chunk_index += 1
                
        return chunks

document_chunker = DocumentChunker()
