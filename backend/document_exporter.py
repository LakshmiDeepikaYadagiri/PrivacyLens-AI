
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Preformatted,
)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle


SUPPORTED_FORMATS = {"txt", "pdf", "docx"}


def export_txt(text):
    return text.encode("utf-8")


def export_docx(text):
    document = Document()

    document.add_heading(
        "PrivacyLens AI - Redacted Document",
        level=1
    )

    document.add_paragraph(
        "Sensitive information has been replaced "
        "with redaction labels."
    )

    document.add_paragraph(
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}"
    )

    document.add_paragraph("")

    for line in text.split("\n"):
        paragraph = document.add_paragraph()
        run = paragraph.add_run(line)
        run.font.size = Pt(10)

    output = BytesIO()
    document.save(output)

    return output.getvalue()


def export_pdf(text):
    output = BytesIO()

    pdf = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    body_style = ParagraphStyle(
        "RedactedBody",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#172033"),
        spaceAfter=3,
        splitLongWords=True,
    )

    story = [
        Paragraph(
            "PrivacyLens AI - Redacted Document",
            styles["Title"]
        ),
        Spacer(1, 12),
        Paragraph(
            "Sensitive information has been replaced "
            "with redaction labels.",
            styles["Normal"]
        ),
        Spacer(1, 16),
    ]

    for line in text.split("\n"):
        if line:
            # Escape user-supplied text so it is
            # displayed as text, not PDF markup.
            story.append(
                Paragraph(escape(line), body_style)
            )
        else:
            story.append(Spacer(1, 10))

    pdf.build(story)

    return output.getvalue()


def create_export(text, file_format):
    file_format = file_format.lower()

    if file_format not in SUPPORTED_FORMATS:
        raise ValueError(
            "Only TXT, PDF, and DOCX exports are supported."
        )

    if file_format == "txt":
        content = export_txt(text)
        media_type = "text/plain; charset=utf-8"

    elif file_format == "pdf":
        content = export_pdf(text)
        media_type = "application/pdf"

    else:
        content = export_docx(text)
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    return content, media_type
