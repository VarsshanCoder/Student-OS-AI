mod chunking;
mod models;
mod pdf;
mod text;
mod validation;

use axum::{
    extract::{DefaultBodyLimit, Multipart},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use models::*;
use std::net::SocketAddr;
use std::time::Instant;
use tower_http::limit::RequestBodyLimitLayer;
use tower_http::timeout::TimeoutLayer;
use tower_http::trace::TraceLayer;
use tracing::{error, info, Level};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    info!("Starting ScholarOS Rust Engine on port 3001...");

    let app = Router::new()
        .route("/health", get(health_check))
        .route("/v1/documents/process", post(process_document))
        // 50 MB limit, 30s timeout
        .layer(DefaultBodyLimit::max(50 * 1024 * 1024))
        .layer(TimeoutLayer::new(std::time::Duration::from_secs(30)))
        .layer(TraceLayer::new_for_http());

    let addr = SocketAddr::from(([127, 0, 0, 1], 3001));
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    
    info!("Listening on {}", addr);
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .unwrap();
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c()
        .await
        .expect("failed to install CTRL+C signal handler");
    info!("Shutdown signal received, starting graceful shutdown...");
}

async fn health_check() -> (StatusCode, &'static str) {
    (StatusCode::OK, "Scholar Engine is running")
}

async fn process_document(
    mut multipart: Multipart,
) -> Result<Json<ProcessDocumentResponse>, (StatusCode, String)> {
    let start_time = Instant::now();
    let mut file_bytes = None;
    let mut document_id = String::new();
    let mut max_chunk_size = 1000;
    let mut chunk_overlap = 100;
    let mut remove_headers = false;

    // Parse multipart form data
    while let Some(field) = multipart.next_field().await.map_err(|e| {
        error!("Multipart error: {}", e);
        (StatusCode::BAD_REQUEST, "Malformed multipart request".into())
    })? {
        let name = field.name().unwrap_or("").to_string();
        if name == "file" {
            let data = field.bytes().await.map_err(|e| {
                error!("Failed to read file bytes: {}", e);
                (StatusCode::BAD_REQUEST, "Invalid file data".into())
            })?;
            file_bytes = Some(data);
        } else if name == "document_id" {
            document_id = field.text().await.unwrap_or_default();
        } else if name == "max_chunk_size" {
            if let Ok(text) = field.text().await {
                if let Ok(val) = text.parse() {
                    max_chunk_size = val;
                }
            }
        } else if name == "chunk_overlap" {
            if let Ok(text) = field.text().await {
                if let Ok(val) = text.parse() {
                    chunk_overlap = val;
                }
            }
        } else if name == "remove_headers" {
            if let Ok(text) = field.text().await {
                remove_headers = text == "true";
            }
        }
    }

    let bytes = file_bytes.ok_or_else(|| {
        (StatusCode::BAD_REQUEST, "Missing file part in request".into())
    })?;

    if document_id.is_empty() {
        return Err((StatusCode::BAD_REQUEST, "Missing document_id".into()));
    }

    info!("Processing document {} ({} bytes)", document_id, bytes.len());

    // 1. PDF Extraction
    let extract_start = Instant::now();
    let mut pages = pdf::PdfExtractor::extract_text(&bytes).map_err(|e| {
        error!("Extraction error: {}", e);
        (StatusCode::UNPROCESSABLE_ENTITY, e)
    })?;
    let extraction_time_ms = extract_start.elapsed().as_millis() as u64;

    // 2. Text Normalization
    let mut total_characters = 0;
    for (_, text) in &mut pages {
        if remove_headers {
            *text = text::TextNormalizer::remove_headers_footers(text);
        }
        *text = text::TextNormalizer::cleanup_whitespace(text);
        total_characters += text.len();
    }
    
    // Combine text for validation
    let full_text = pages.iter().map(|(_, t)| t.as_str()).collect::<Vec<_>>().join("\n");
    let validation = validation::MarkdownValidator::validate(&full_text);

    // 3. Chunking
    let chunking_start = Instant::now();
    let chunks = chunking::Chunker::generate_chunks(pages.clone(), max_chunk_size, chunk_overlap);
    let chunking_time_ms = chunking_start.elapsed().as_millis() as u64;

    let response = ProcessDocumentResponse {
        document_id,
        metadata: DocumentMetadata {
            page_count: pages.len(),
            total_characters,
        },
        chunks,
        stats: ProcessingStats {
            extraction_time_ms,
            chunking_time_ms,
        },
        validation,
    };

    info!("Completed document processing in {}ms", start_time.elapsed().as_millis());
    Ok(Json(response))
}
