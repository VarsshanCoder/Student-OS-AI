use crate::models::ValidationResults;

pub struct MarkdownValidator;

impl MarkdownValidator {
    pub fn validate(text: &str) -> ValidationResults {
        let mut issues = Vec::new();
        
        // Example logic: checks for unclosed brackets or mismatched backticks
        let open_brackets = text.matches('[').count();
        let close_brackets = text.matches(']').count();
        if open_brackets != close_brackets {
            issues.push(format!("Mismatched brackets: {} open, {} close", open_brackets, close_brackets));
        }
        
        let backticks = text.matches("```").count();
        if backticks % 2 != 0 {
            issues.push("Unclosed code blocks detected".to_string());
        }
        
        ValidationResults {
            is_valid_markdown: issues.is_empty(),
            issues_found: issues,
        }
    }
}
