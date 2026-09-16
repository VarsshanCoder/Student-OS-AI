use crate::models::DocumentChunk;
use regex::Regex;

pub struct Chunker;

impl Chunker {
    pub fn generate_chunks(
        pages: Vec<(usize, String)>, 
        max_size: usize, 
        overlap: usize
    ) -> Vec<DocumentChunk> {
        let mut chunks = Vec::new();
        let mut chunk_index = 0;
        
        let split_re = Regex::new(r"\n\s*\n").unwrap();
        
        for (page_number, text) in pages {
            let paragraphs: Vec<&str> = split_re.split(&text).collect();
            let mut current_chunk = String::new();
            
            for para in paragraphs {
                let para = para.trim();
                if para.is_empty() {
                    continue;
                }
                
                let delimiter_len = if current_chunk.is_empty() { 0 } else { 2 };
                
                if current_chunk.len() + delimiter_len + para.len() > max_size && !current_chunk.is_empty() {
                    chunks.push(DocumentChunk {
                        chunk_index,
                        page_number,
                        content: current_chunk.trim().to_string(),
                    });
                    chunk_index += 1;
                    
                    // Simple overlap: take last 'overlap' characters safely
                    let overlap_str = if current_chunk.len() > overlap {
                        let start = current_chunk.len() - overlap;
                        // Avoid splitting in middle of characters, find space if possible
                        match current_chunk[start..].find(' ') {
                            Some(idx) => &current_chunk[start + idx + 1..],
                            None => &current_chunk[start..],
                        }
                    } else {
                        ""
                    };
                    
                    current_chunk = format!("{}\n\n{}", overlap_str, para);
                } else {
                    if !current_chunk.is_empty() {
                        current_chunk.push_str("\n\n");
                    }
                    current_chunk.push_str(para);
                }
            }
            
            if !current_chunk.trim().is_empty() {
                chunks.push(DocumentChunk {
                    chunk_index,
                    page_number,
                    content: current_chunk.trim().to_string(),
                });
                chunk_index += 1;
            }
        }
        
        chunks
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_chunks() {
        let pages = vec![
            (1, "Para 1.\n\nPara 2.".to_string()),
            (2, "Para 3 is very long and will exceed the chunk limit if limit is small.".to_string())
        ];
        
        // Use a small max_size to force splitting
        let chunks = Chunker::generate_chunks(pages, 15, 5);
        
        assert!(!chunks.is_empty());
        assert_eq!(chunks[0].page_number, 1);
        
        // First para
        assert_eq!(chunks[0].content, "Para 1.");
    }
}
