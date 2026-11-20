
import os
from io import BytesIO

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Request,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from pydantic import BaseModel

from backend.document_exporter import create_export

from backend.chunk_processor import (
    analyze_large_text,
    validate_text,
    MAX_CHARACTERS,
)

from backend.redactor import redact_text
from backend.risk_score import calculate_risk

from backend.file_processor import (
    process_document,
    DocumentProcessingError,
    MAX_FILE_BYTES,
)


# ==========================================
# Create FastAPI application
# ==========================================

app = FastAPI(
    title="PrivacyLens AI",
    description="AI-powered sensitive data detection and redaction",
    version="2.0.0",
)


# ==========================================
# CORS configuration for local and cloud
# ==========================================

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

frontend_url = os.getenv(
    "FRONTEND_URL", ""
).strip().rstrip("/")

if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ==========================================
# Security middleware
# ==========================================

@app.middleware("http")
async def prevent_sensitive_response_caching(
    request: Request,
    call_next,
):
    response: Response = await call_next(request)

    if request.url.path in {
        "/upload",
        "/detect",
        "/redact",
        "/risk-score",
        "/export",
    }:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"

    return response


# ==========================================
# Request models
# ==========================================

class TextRequest(BaseModel):
    text: str


class ExportRequest(BaseModel):
    text: str
    file_format: str


# ==========================================
# Input validation
# ==========================================

def check_input(text):
    try:
        validate_text(text)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ==========================================
# Home endpoint
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Welcome to PrivacyLens AI!",
        "status": "Backend is running successfully",
        "version": "2.0.0",
        "max_characters": MAX_CHARACTERS,
        "chunking_enabled": True,
        "file_upload_enabled": True,
        "supported_files": [
            "TXT",
            "PDF",
            "DOCX",
        ],
    }


# ==========================================
# Upload TXT, PDF, or DOCX documents
# ==========================================

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    try:
        content = await file.read(
            MAX_FILE_BYTES + 1
        )

        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Maximum file size is 10 MB.",
            )

        result = process_document(
            filename=file.filename,
            content=content,
        )

        return result

    except DocumentProcessingError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    finally:
        await file.close()


# ==========================================
# Detect sensitive information
# ==========================================

@app.post("/detect")
def detect_sensitive_data(
    request: TextRequest
):
    check_input(request.text)

    results, total_chunks = analyze_large_text(
        request.text
    )

    detections = []

    for result in results:
        detections.append({
            "type": result.entity_type,
            "text": request.text[
                result.start:result.end
            ],
            "confidence": round(
                result.score, 2
            ),
        })

    return {
        "detections": detections,
        "total_detected": len(detections),
        "total_chunks": total_chunks,
    }


# ==========================================
# Redact sensitive information
# ==========================================

@app.post("/redact")
def redact_sensitive_data(
    request: TextRequest
):
    check_input(request.text)

    result = redact_text(request.text)

    return result


# ==========================================
# Calculate privacy risk score
# ==========================================

@app.post("/risk-score")
def get_risk_score(
    request: TextRequest
):
    check_input(request.text)

    result = calculate_risk(request.text)

    return result


# ==========================================
# Export redacted documents
# ==========================================

@app.post("/export")
def export_redacted_document(
    request: ExportRequest
):
    check_input(request.text)

    file_format = request.file_format.lower()

    if file_format not in {
        "txt",
        "pdf",
        "docx",
    }:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format.",
        )

    # Re-run redaction on the server.
    # Never trust browser-provided redacted text.

    result = redact_text(request.text)

    protected_text = result["redacted_text"]

    try:
        content, media_type = create_export(
            protected_text,
            file_format,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the document.",
        )

    filename = (
        f"PrivacyLens_Redacted.{file_format}"
    )

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Cache-Control": "no-store",
        },
    )
