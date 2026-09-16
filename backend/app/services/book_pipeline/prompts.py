import json
from app.ai.router.ai_router import ai_router

OUTLINE_PROMPT = """You are an expert academic curriculum designer. 
Create a detailed chapter outline for a book titled "Knowledge Book: {topic}".
Level: {level}
Language: {language}
Style: {style}
Target length: {target_length}
Optional Syllabus context: {syllabus}

Output valid JSON ONLY in this format:
{{
  "title": "...",
  "chapters": [
    {{
      "title": "Chapter 1: ...",
      "order": 1,
      "learning_objectives": ["...", "..."],
      "sections": ["...", "..."]
    }}
  ]
}}
"""

CHAPTER_PROMPT = """You are an expert textbook author.
Write the complete content for the following chapter in Markdown format.

Book Topic: {topic}
Chapter Title: {chapter_title}
Objectives: {objectives}
Sections to cover: {sections}
Style: {style}
Language: {language}

Requirements:
1. Output ONLY valid Markdown. Do not wrap in ```markdown ... ```
2. Use headings (##, ###), lists, and bold text.
3. Include conceptual explanations, examples, and key points.
4. Include a summary and 3-5 review questions at the end.
5. Use code blocks with appropriate syntax highlighting if code is needed.
6. Use LaTeX for math equations if relevant.
"""

async def generate_outline(topic, level, language, style, target_length, syllabus=""):
    prompt = OUTLINE_PROMPT.format(
        topic=topic, level=level, language=language, style=style, 
        target_length=target_length, syllabus=syllabus
    )
    
    response = await ai_router.generate_completion(
        user_id="system",
        task_category="COMPLEX",
        prompt=prompt,
        require_json=True
    )
    return json.loads(response["text"])

async def generate_chapter_content(topic, chapter_title, objectives, sections, style, language):
    prompt = CHAPTER_PROMPT.format(
        topic=topic, chapter_title=chapter_title, objectives=objectives, 
        sections=sections, style=style, language=language
    )
    
    response = await ai_router.generate_completion(
        user_id="system",
        task_category="COMPLEX",
        prompt=prompt,
        require_json=False
    )
    return response["text"]
