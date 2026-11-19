
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, BadZipFile

import fitz
from docx import Document


# --------------------------------------------------
# File upload limits
# --------------------------------------------------

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARACTERS = 25000

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}

# DOCX archive security limits
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_ENTRIES = 1000


# --------------------------------------------------
# Custom exception
# --------------------------------------------------

class DocumentProcessingError(Exception):
    pass


# --------------------------------------------------
# Validate file signatures
# --------------------------------------------------

def validate_file_signature(extension, content):
    """Check basic PDF and DOCX file signatures."""

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentProcessingError(
                "Invalid PDF file format."
            )

    elif extension == ".docx":
        if not content.startswith(b"PK"):
            raise DocumentProcessingError(
                "Invalid DOCX file format."
            )


# --------------------------------------------------
# Validate DOCX archive safety
# --------------------------------------------------

def validate_docx_archive(content):
    """Reject oversized or suspicious DOCX archives."""

    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()

            # Reject excessive archive entries
            if len(entries) > MAX_DOCX_ENTRIES:
                raise DocumentProcessingError(
                    "DOCX contains too many archive entries."
                )

            total_size = 0

            for entry in entries:
                total_size += entry.file_size

                if (
                    total_size
                    > MAX_DOCX_UNCOMPRESSED_BYTES
                ):
                    raise DocumentProcessingError(
                        "DOCX uncompressed size exceeds "
                        "the 50 MB safety limit."
                    )

            # Verify basic DOCX structure
            if (
                "[Content_Types].xml"
                not in archive.namelist()
            ):
                raise DocumentProcessingError(
                    "Invalid DOCX document structure."
                )

    except DocumentProcessingError:
        raise

    except (BadZipFile, OSError, ValueError):
        raise DocumentProcessingError(
            "Invalid or corrupted DOCX archive."
        )


# --------------------------------------------------
# Extract TXT content
# --------------------------------------------------


def extract_txt(content):
    """Extract text from a UTF-8 text file."""

    try:
        return content.decode("utf-8-sig")

    except UnicodeDecodeError:
        raise DocumentProcessingError(
            "Unable to read this TXT file. "
            "Please save the file using UTF-8 encoding."
        )

def extract_pdf(content):
    pages = []
    total_characters = 0

    try:
        with fitz.open(
            stream=content,
            filetype="pdf"
        ) as document:

            if document.needs_pass:
                raise DocumentProcessingError(
                    "Password-protected PDFs are not supported."
                )

            if len(document) > MAX_PDF_PAGES:
                raise DocumentProcessingError(
                    "PDF exceeds the 100-page safety limit."
                )

            for page in document:
                page_text = page.get_text("text")

                if pages:
                    total_characters += 1

                total_characters += len(page_text)

                if total_characters > MAX_TEXT_CHARACTERS:
                    raise DocumentProcessingError(
                        "PDF text exceeds the "
                        "25,000-character safety limit."
                    )

                pages.append(page_text)

    except DocumentProcessingError:
        raise

    except Exception:
        raise DocumentProcessingError(
            "Unable to read this PDF file."
        )

    return "\n".join(pages)



# --------------------------------------------------
# Extract PDF content
# --------------------------------------------------



# --------------------------------------------------
# Extract DOCX content
# --------------------------------------------------

def extract_docx(content):
    try:
        document = Document(BytesIO(content))

        from docx.oxml.ns import qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table

        lines = []

        # Preserve paragraphs and tables in order
        for element in document.element.body.iterchildren():

            if element.tag == qn("w:p"):
                paragraph = Paragraph(
                    element,
                    document
                )

                if paragraph.text.strip():
                    lines.append(
                        paragraph.text
                    )

            elif element.tag == qn("w:tbl"):
                table = Table(
                    element,
                    document
                )

                for row in table.rows:
                    values = [
                        cell.text.strip()
                        for cell in row.cells
                    ]

                    lines.append(
                        " | ".join(values)
                    )

        return "\n".join(lines)

    except Exception:
        raise DocumentProcessingError(
            "Unable to read this DOCX file."
        )


# --------------------------------------------------
# Process uploaded document
# --------------------------------------------------

def process_document(filename, content):

    # Get file extension
    extension = Path(
        filename or ""
    ).suffix.lower()

    # Validate supported file types
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentProcessingError(
            "Only TXT, PDF, and DOCX files "
            "are supported."
        )

    # Reject empty files
    if not content:
        raise DocumentProcessingError(
            "The uploaded file is empty."
        )

    # Enforce 10 MB upload limit
    if len(content) > MAX_FILE_BYTES:
        raise DocumentProcessingError(
            "File size must not exceed 10 MB."
        )

    # Validate file signature
    validate_file_signature(
        extension,
        content
    )

    # Additional DOCX security validation
    if extension == ".docx":
        validate_docx_archive(content)

    # Extract document text
    if extension == ".txt":
        text = extract_txt(content)

    elif extension == ".pdf":
        text = extract_pdf(content)

    else:
        text = extract_docx(content)

    # Reject documents without readable text
    if not text.strip():
        raise DocumentProcessingError(
            "No readable text was found. "
            "Scanned PDFs require OCR, "
            "which is not included "
            "in this version."
        )

    # Enforce extracted text limit
    if len(text) > MAX_TEXT_CHARACTERS:
        raise DocumentProcessingError(
            "The extracted text contains "
            f"{len(text):,} characters. "
            "The current limit is "
            "25,000 characters."
        )

    # Return extracted document information
    return {
        "filename": Path(filename).name,
        "file_type": extension.upper().replace(
            ".", ""
        ),
        "file_size": len(content),
        "text": text,
        "character_count": len(text),
    }
MAX_PDF_PAGES = 100
