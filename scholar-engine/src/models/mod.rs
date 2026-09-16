use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct ProcessDocumentRequest {
    pub document_id: String,
    pub processing_options: ProcessingOptions,
}

#[derive(Debug, Deserialize)]
pub struct ProcessingOptions {
    pub max_chunk_size: usize,
    pub chunk_overlap: usize,
    pub remove_headers: bool,
}

#[derive(Debug, Serialize)]
pub struct ProcessDocumentResponse {
    pub document_id: String,
    pub metadata: DocumentMetadata,
    pub chunks: Vec<DocumentChunk>,
    pub stats: ProcessingStats,
    pub validation: ValidationResults,
}

#[derive(Debug, Serialize)]
pub struct DocumentMetadata {
    pub page_count: usize,
    pub total_characters: usize,
}

#[derive(Debug, Serialize)]
pub struct DocumentChunk {
    pub chunk_index: usize,
    pub page_number: usize,
    pub content: String,
}

#[derive(Debug, Serialize)]
pub struct ProcessingStats {
    pub extraction_time_ms: u64,
    pub chunking_time_ms: u64,
}

#[derive(Debug, Serialize)]
pub struct ValidationResults {
    pub is_valid_markdown: bool,
    pub issues_found: Vec<String>,
}
