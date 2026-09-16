use regex::Regex;

pub struct TextNormalizer;

impl TextNormalizer {
    pub fn cleanup_whitespace(text: &str) -> String {
        // Collapse multiple spaces
        let re_spaces = Regex::new(r"[ \t]+").unwrap();
        let s1 = re_spaces.replace_all(text, " ");
        
        // Collapse more than 2 newlines into just 2 newlines
        let re_newlines = Regex::new(r"\n{3,}").unwrap();
        re_newlines.replace_all(&s1, "\n\n").into_owned()
    }
    
    pub fn remove_headers_footers(text: &str) -> String {
        // Very basic stub: remove lines starting with 'Page X'
        let re = Regex::new(r"(?im)^Page \d+$").unwrap();
        re.replace_all(text, "").into_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cleanup_whitespace() {
        let input = "This   is  a\n\n\ntest\n\n\n\nstring.";
        let expected = "This is a\n\ntest\n\nstring.";
        assert_eq!(TextNormalizer::cleanup_whitespace(input), expected);
    }
    
    #[test]
    fn test_remove_headers() {
        let input = "Header\nContent\nPage 4\nMore content";
        let expected = "Header\nContent\n\nMore content";
        assert_eq!(TextNormalizer::remove_headers_footers(input), expected);
    }
}
