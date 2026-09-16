import io
from typing import List, Dict, Any
import pypdf

class DocumentParser:
    """
    Parses documents (PDFs) into raw text with page markers.
    Architected to be swappable with a future Rust extraction engine.
    """
    
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extracts text from a PDF, maintaining page numbers.
        Returns a list of dicts: {"page_number": int, "text": str}
        """
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_data = []
        
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                pages_data.append({
                    "page_number": i + 1,
                    "text": text.strip()
                })
                
        return pages_data

document_parser = DocumentParser()
