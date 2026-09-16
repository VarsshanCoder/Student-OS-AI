import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ScholarEngineClient:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=35.0) # Matches 30s engine timeout + buffer
        
    async def process_document(
        self, 
        document_id: str, 
        file_bytes: bytes, 
        max_chunk_size: int = 1000, 
        chunk_overlap: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Delegates CPU-intensive PDF extraction and chunking to the Rust Scholar Engine.
        Returns None if the engine is unavailable or fails.
        """
        url = f"{self.base_url}/v1/documents/process"
        
        files = {'file': ('document.pdf', file_bytes, 'application/pdf')}
        data = {
            'document_id': document_id,
            'max_chunk_size': str(max_chunk_size),
            'chunk_overlap': str(chunk_overlap),
            'remove_headers': 'true'
        }
        
        try:
            response = await self.client.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.warning(f"Scholar Engine unavailable or network error: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Scholar Engine processing failed with status {e.response.status_code}: {e.response.text}")
            return None
            
scholar_engine_client = ScholarEngineClient()
