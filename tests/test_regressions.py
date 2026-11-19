
import pytest

from backend.chunk_processor import (
    analyze_large_text,
    create_chunks,
    resolve_phone_conflicts,
)
from presidio_analyzer import RecognizerResult


def detect(text):
    results, _ = analyze_large_text(text)
    return [
        (
            result.entity_type,
            text[result.start:result.end],
        )
        for result in results
    ]


@pytest.mark.parametrize(
    "phone",
    [
        "617-555-0129",
        "(415) 555-0198",
        "+1 303-555-0125",
        "212 555 0147",
    ],
)
def test_us_phone_formats(phone):
    text = f"Call me at {phone}"
    assert ("PHONE_NUMBER", phone) in detect(text)


def test_uk_nhs_phone_conflict():
    text = "My number is 617-555-0129"

    results = detect(text)

    assert (
        "PHONE_NUMBER",
        "617-555-0129",
    ) in results

    assert (
        "UK_NHS",
        "617-555-0129",
    ) not in results


def test_genuine_nhs_identifier_preserved():
    text = "9434765919"

    nhs_result = RecognizerResult(
        entity_type="UK_NHS",
        start=0,
        end=len(text),
        score=1.0,
    )

    resolved = resolve_phone_conflicts(
        [nhs_result],
        text,
    )

    assert len(resolved) == 1
    assert resolved[0].entity_type == "UK_NHS"


def test_email_detection_regression():
    text = "Contact admin42@example.org"

    results = detect(text)

    assert (
        "EMAIL_ADDRESS",
        "admin42@example.org",
    ) in results

    assert (
        "LOCATION",
        "Contact",
    ) not in results


def test_custom_id_regression():
    text = "Student ID: ZX987654"

    assert (
    "CUSTOM_ID",
    "ZX987654",
) in detect(text)


def test_address_regression():
    text = "Send it to 2468 Cedar Road, Austin, TX"

    assert (
        "LOCATION",
        "2468 Cedar Road, Austin, TX",
    ) in detect(text)


def test_repeated_emails_have_distinct_offsets():
    text = (
        "First: team@example.com. "
        "Second: team@example.com."
    )

    results, _ = analyze_large_text(text)

    emails = [
        result
        for result in results
        if (
            result.entity_type == "EMAIL_ADDRESS"
            and text[result.start:result.end]
            == "team@example.com"
        )
    ]

    assert len(emails) == 2
    assert emails[0].start != emails[1].start


def test_chunk_boundaries_are_valid():
    text = (
        "This is ordinary text. " * 180
    )

    chunks = create_chunks(text)

    assert len(chunks) > 1

    for chunk in chunks:
        assert (
            chunk["text"]
            == text[chunk["start"]:chunk["end"]]
        )

        assert len(chunk["text"]) <= 2000


def test_overlapping_chunk_detections_are_deduplicated():
    text = (
        "Normal information. " * 90
        + "Contact: user@example.com. "
        + "Normal information. " * 20
    )

    results, _ = analyze_large_text(text)

    email_results = [
        result
        for result in results
        if (
            result.entity_type == "EMAIL_ADDRESS"
            and text[result.start:result.end]
            == "user@example.com"
        )
    ]

    assert len(email_results) == 1

def test_reach_email_false_positive():
    text = "Reach support77@demo.org"

    results = detect(text)

    assert (
        "EMAIL_ADDRESS",
        "support77@demo.org",
    ) in results

    assert (
        "ORGANIZATION",
        "Reach",
    ) not in results

from backend.file_processor import (
    process_document,
    DocumentProcessingError,
)


def test_fake_pdf_rejected():
    with pytest.raises(DocumentProcessingError):
        process_document(
            "fake.pdf",
            b"This is not a PDF document.",
        )


def test_fake_docx_rejected():
    with pytest.raises(DocumentProcessingError):
        process_document(
            "fake.docx",
            b"This is not a Word document.",
        )


def test_unsupported_extension_rejected():
    with pytest.raises(DocumentProcessingError):
        process_document(
            "script.exe",
            b"Example content",
        )


def test_empty_upload_rejected():
    with pytest.raises(DocumentProcessingError):
        process_document(
            "empty.txt",
            b"",
        )

from io import BytesIO
from zipfile import ZipFile, ZIP_STORED




def test_oversized_docx_archive_rejected():
    from io import BytesIO
    from zipfile import ZipFile, ZIP_DEFLATED

    from backend.file_processor import (
        MAX_FILE_BYTES,
        MAX_DOCX_UNCOMPRESSED_BYTES,
        DocumentProcessingError,
        process_document,
    )

    buffer = BytesIO()

    with ZipFile(
        buffer,
        "w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:

        archive.writestr(
            "[Content_Types].xml",
            "<Types></Types>",
        )

        archive.writestr(
            "word/document.xml",
            b"A" * (MAX_DOCX_UNCOMPRESSED_BYTES + 1),
        )

    content = buffer.getvalue()

    assert len(content) < MAX_FILE_BYTES

    with pytest.raises(
        DocumentProcessingError,
        match="50 MB safety limit",
    ):
        process_document(
            "oversized.docx",
            content,
        )



def test_pdf_page_limit():
    import fitz
    import pytest

    from backend.file_processor import (
        process_document,
        DocumentProcessingError,
        MAX_PDF_PAGES,
    )

    with fitz.open() as document:
        for _ in range(MAX_PDF_PAGES + 1):
            document.new_page()

        content = document.tobytes()

    with pytest.raises(
        DocumentProcessingError,
        match="100-page safety limit",
    ):
        process_document("large.pdf", content)


def test_pdf_text_limit():
    import fitz
    import pytest

    from backend.file_processor import (
        process_document,
        DocumentProcessingError,
        MAX_TEXT_CHARACTERS,
    )

    text = ("PrivacyLens security test.\n" * 80)

    with fitz.open() as document:
        for _ in range(20):
            page = document.new_page(
                width=1000,
                height=2000,
            )

            page.insert_text(
                (50, 50),
                text,
                fontsize=10,
            )

        extracted_text = "\n".join(
            page.get_text("text")
            for page in document
        )

        assert len(extracted_text) > MAX_TEXT_CHARACTERS

        content = document.tobytes()

    with pytest.raises(
        DocumentProcessingError,
        match="25,000-character safety limit",
    ):
        process_document("large_text.pdf", content)


def test_password_protected_pdf():
    import fitz
    import pytest

    from backend.file_processor import (
        process_document,
        DocumentProcessingError,
    )

    with fitz.open() as document:
        page = document.new_page()

        page.insert_text(
            (50, 50),
            "Confidential document",
        )

        content = document.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner123",
            user_pw="password123",
        )

    with pytest.raises(
        DocumentProcessingError,
        match="Password-protected",
    ):
        process_document("protected.pdf", content)



def test_successful_txt_processing():
    from backend.file_processor import process_document

    text = "Contact Emily at emily@example.com."
    content = text.encode("utf-8")

    result = process_document("sample.txt", content)

    assert result["file_type"] == "TXT"
    assert result["text"].strip() == text
    assert result["character_count"] > 0


def test_successful_pdf_processing():
    import fitz
    from backend.file_processor import process_document

    with fitz.open() as document:
        page = document.new_page()

        page.insert_text(
            (50, 50),
            "Contact Emily at emily@example.com."
        )

        content = document.tobytes()

    result = process_document("sample.pdf", content)

    assert result["file_type"] == "PDF"
    assert "emily@example.com" in result["text"]
    assert result["character_count"] > 0


def test_successful_docx_processing():
    from io import BytesIO
    from docx import Document
    from backend.file_processor import process_document

    document = Document()

    document.add_paragraph(
        "Contact Emily at emily@example.com."
    )

    buffer = BytesIO()
    document.save(buffer)

    result = process_document(
        "sample.docx",
        buffer.getvalue()
    )

    assert result["file_type"] == "DOCX"
    assert "emily@example.com" in result["text"]
    assert result["character_count"] > 0

def test_hyphenated_employee_id():
    text = "Employee ID: EMP-2026-1045"

    assert (
        "CUSTOM_ID",
        "EMP-2026-1045",
    ) in detect(text)


def test_employee_id_redaction_preserves_label():
    from backend.redactor import redact_text

    text = "Employee ID: EMP-2026-1045"

    result = redact_text(text)

    assert "Employee ID: [CUSTOM_ID]" in result["redacted_text"]
    assert "EMP-2026-1045" not in result["redacted_text"]
