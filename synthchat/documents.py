import os
import uuid
import csv
import io
import textwrap
from pathlib import Path

DOCUMENTS_DIR = os.path.expanduser("~/.octobot/synthchat/documents")

os.makedirs(DOCUMENTS_DIR, exist_ok=True)

DOCUMENT_TOOL_DEFINITIONS = [
    {
        "name": "create_document",
        "description": (
            "Create a downloadable document file. Use this to save research findings, "
            "data tables, reports, or code as a file the user can download. "
            "Supported formats: csv, html, pdf, png."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name for the file (without extension). Example: 'research-findings'",
                },
                "content": {
                    "type": "string",
                    "description": (
                        "The document content. For CSV: comma-separated rows with headers. "
                        "For HTML: full or partial HTML markup. "
                        "For PDF: plain text or markdown-like text (headings with #, bullets with -, paragraphs). "
                        "For PNG: text content to render as a styled info card."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["csv", "html", "pdf", "png"],
                    "description": "Output format: csv, html, pdf, or png",
                },
                "title": {
                    "type": "string",
                    "description": "Document title (used in PDF header and HTML title). Optional.",
                },
            },
            "required": ["filename", "content", "format"],
        },
    },
]

_DOCUMENT_TOOL_NAMES = {t["name"] for t in DOCUMENT_TOOL_DEFINITIONS}


def _sanitize_filename(name):
    safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
    safe = safe.strip().replace(" ", "-")
    return safe[:60] or "document"


def _create_csv(filepath, content):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        f.write(content)


def _create_html(filepath, content, title=""):
    if "<html" not in content.lower() and "<body" not in content.lower():
        content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title or 'Document'}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.6; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #00e5c8; padding-bottom: 8px; }}
h2 {{ color: #2d3748; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
th {{ background: #f7fafc; font-weight: 600; }}
tr:nth-child(even) {{ background: #f7fafc; }}
code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
pre {{ background: #1a1d21; color: #e0e0e0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
a {{ color: #00a896; }}
</style>
</head>
<body>
{f'<h1>{title}</h1>' if title else ''}
{content}
</body>
</html>"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _create_pdf(filepath, content, title=""):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pw = pdf.w - pdf.l_margin - pdf.r_margin

    if title:
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(pw, 12, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    lines = content.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            pdf.ln(4)
            continue

        clean = stripped.replace("**", "").replace("*", "")

        if stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(pw, 8, clean[4:].strip(), new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(pw, 9, clean[3:].strip(), new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(pw, 10, clean[2:].strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 11)
            text = clean[2:].strip()
            pdf.cell(pw, 6, "    - " + text, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(pw, 6, clean)

    pdf.output(filepath)


def _create_png(filepath, content, title=""):
    from PIL import Image, ImageDraw, ImageFont

    padding = 40
    width = 800
    line_height = 24
    title_height = 40

    lines = []
    for raw_line in content.split("\n"):
        wrapped = textwrap.wrap(raw_line, width=80) or [""]
        lines.extend(wrapped)

    content_height = len(lines) * line_height
    total_height = padding * 2 + content_height + (title_height if title else 0) + 20

    img = Image.new("RGB", (width, total_height), color="#1a1d21")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
        font_bold = font
        font_title = font

    draw.rectangle([(0, 0), (width, 4)], fill="#00e5c8")

    y = padding
    if title:
        draw.text((padding, y), title, fill="#00e5c8", font=font_title)
        y += title_height

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            draw.text((padding, y), stripped[2:], fill="#ffffff", font=font_bold)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            draw.text((padding + 10, y), f"- {stripped[2:]}", fill="#e0e0e0", font=font)
        else:
            draw.text((padding, y), stripped, fill="#e0e0e0", font=font)
        y += line_height

    img.save(filepath, "PNG")


def create_document(filename, content, fmt, title=""):
    doc_id = uuid.uuid4().hex[:8]
    safe_name = _sanitize_filename(filename)
    full_filename = f"{doc_id}_{safe_name}.{fmt}"
    filepath = os.path.join(DOCUMENTS_DIR, full_filename)

    if fmt == "csv":
        _create_csv(filepath, content)
    elif fmt == "html":
        _create_html(filepath, content, title)
    elif fmt == "pdf":
        _create_pdf(filepath, content, title)
    elif fmt == "png":
        _create_png(filepath, content, title)
    else:
        return {"error": f"Unsupported format: {fmt}"}

    size = os.path.getsize(filepath)

    return {
        "id": doc_id,
        "filename": full_filename,
        "display_name": f"{safe_name}.{fmt}",
        "format": fmt,
        "size": size,
        "url": f"/api/documents/{doc_id}/{full_filename}",
    }


def execute_document_tool(tool_name, tool_input):
    if tool_name == "create_document":
        result = create_document(
            filename=tool_input["filename"],
            content=tool_input["content"],
            fmt=tool_input["format"],
            title=tool_input.get("title", ""),
        )
        import json
        return json.dumps(result)
    return json.dumps({"error": f"Unknown document tool: {tool_name}"})
