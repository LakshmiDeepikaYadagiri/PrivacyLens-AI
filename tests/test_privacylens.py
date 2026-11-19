
import pytest
from fastapi.testclient import TestClient
from presidio_analyzer import RecognizerResult

from backend.main import app
from backend.chunk_processor import (
    MAX_CHARACTERS,
    create_chunks,
    validate_text,
    analyze_large_text,
)
from backend.overlap_filter import (
    remove_overlapping_detections,
)
from backend.redactor import redact_text


client = TestClient(app)


# ----------------------------
# Input validation tests
# ----------------------------

def test_empty_input_rejected():
    with pytest.raises(ValueError):
        validate_text("")


def test_whitespace_input_rejected():
    with pytest.raises(ValueError):
        validate_text("   ")


def test_maximum_input_accepted():
    validate_text("A" * MAX_CHARACTERS)


def test_oversized_input_rejected():
    with pytest.raises(ValueError):
        validate_text("A" * (MAX_CHARACTERS + 1))


# ----------------------------
# Chunking tests
# ----------------------------

def test_short_text_single_chunk():
    chunks = create_chunks("Hello world")

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Hello world"


def test_large_text_multiple_chunks():
    text = "This is a test sentence. " * 1000

    chunks = create_chunks(text)

    assert len(chunks) > 1
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] == len(text)


def test_chunks_preserve_original_text():
    text = "Hello world. " * 1000

    chunks = create_chunks(text)

    for chunk in chunks:
        assert (
            chunk["text"]
            == text[chunk["start"]:chunk["end"]]
        )


# ----------------------------
# Overlap filter tests
# ----------------------------

def test_overlapping_results_removed():
    results = [
        RecognizerResult(
            entity_type="PERSON",
            start=0,
            end=10,
            score=0.60,
        ),
        RecognizerResult(
            entity_type="PERSON",
            start=0,
            end=10,
            score=0.95,
        ),
    ]

    filtered = remove_overlapping_detections(
        results
    )

    assert len(filtered) == 1
    assert filtered[0].score == 0.95


def test_nonoverlapping_results_preserved():
    results = [
        RecognizerResult(
            entity_type="PERSON",
            start=0,
            end=4,
            score=0.85,
        ),
        RecognizerResult(
            entity_type="EMAIL_ADDRESS",
            start=10,
            end=25,
            score=1.0,
        ),
    ]

    filtered = remove_overlapping_detections(
        results
    )

    assert len(filtered) == 2


# ----------------------------
# Real detector tests
# ----------------------------

def test_email_detection():
    text = "Email: john@example.com"

    results, chunks = analyze_large_text(text)

    assert chunks == 1

    assert any(
        result.entity_type == "EMAIL_ADDRESS"
        and text[result.start:result.end]
        == "john@example.com"
        for result in results
    )


def test_custom_id_detection():
    text = "Student ID: AB123456"

    results, _ = analyze_large_text(text)

    assert any(
        result.entity_type == "CUSTOM_ID"
        for result in results
    )


# ----------------------------
# Redaction tests
# ----------------------------

def test_email_redaction():
    text = "Contact john@example.com"

    result = redact_text(text)

    assert "john@example.com" not in (
        result["redacted_text"]
    )

    assert "[EMAIL_ADDRESS]" in (
        result["redacted_text"]
    )


def test_custom_id_redaction():
    text = "Student ID: AB123456"

    result = redact_text(text)

    assert "AB123456" not in (
        result["redacted_text"]
    )

    assert "[CUSTOM_ID]" in (
        result["redacted_text"]
    )


# ----------------------------
# FastAPI tests
# ----------------------------

def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200


def test_detect_endpoint():
    response = client.post(
        "/detect",
        json={
            "text": "Email: john@example.com"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "detections" in data
    assert "total_detected" in data
    assert "total_chunks" in data


def test_redact_endpoint():
    response = client.post(
        "/redact",
        json={
            "text": "Email: john@example.com"
        },
    )

    assert response.status_code == 200

    assert "[EMAIL_ADDRESS]" in (
        response.json()["redacted_text"]
    )


def test_risk_score_endpoint():
    response = client.post(
        "/risk-score",
        json={
            "text": "Email: john@example.com"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert 0 <= data["risk_score"] <= 100


def test_api_rejects_oversized_input():
    response = client.post(
        "/detect",
        json={
            "text": "A" * (MAX_CHARACTERS + 1)
        },
    )

    assert response.status_code == 400


def test_api_rejects_empty_input():
    response = client.post(
        "/detect",
        json={"text": ""},
    )

    assert response.status_code == 400
