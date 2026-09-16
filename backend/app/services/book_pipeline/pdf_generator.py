import os
import markdown
from xhtml2pdf import pisa
import logging

logger = logging.getLogger(__name__)

def convert_markdown_to_pdf(markdown_content: str, output_path: str) -> bool:
    """Converts a Markdown string to a PDF file deterministically."""
    html_content = markdown.markdown(
        markdown_content, 
        extensions=['extra', 'codehilite', 'tables', 'toc']
    )
    
    # Wrap in basic HTML structure for PDF styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4 portrait;
                margin: 2cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
            }}
            code {{
                font-family: Consolas, monospace;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    try:
        with open(output_path, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(full_html, dest=result_file)
            return not pisa_status.err
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return False
