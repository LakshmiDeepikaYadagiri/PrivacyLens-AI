
import re

from backend.detector import analyzer
from backend.overlap_filter import (
    remove_overlapping_detections,
)

MAX_CHARACTERS = 25000
CHUNK_SIZE = 2000
OVERLAP_SIZE = 200


def validate_text(text):
    if not isinstance(text, str):
        raise ValueError("Input must be text.")

    if not text.strip():
        raise ValueError("Please enter some text.")

    if len(text) > MAX_CHARACTERS:
        raise ValueError(
            f"Maximum input size is "
            f"{MAX_CHARACTERS:,} characters."
        )


def create_chunks(text):
    """
    Create overlapping chunks while preserving
    original character positions.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        target_end = min(
            start + CHUNK_SIZE,
            length,
        )

        end = target_end

        if target_end < length:
            search_start = start + CHUNK_SIZE // 2

            candidates = [
                text.rfind(
                    "\n",
                    search_start,
                    target_end,
                ),
                text.rfind(
                    ". ",
                    search_start,
                    target_end,
                ),
                text.rfind(
                    " ",
                    search_start,
                    target_end,
                ),
            ]

            boundary = max(candidates)

            if boundary > start:
                end = boundary + 1

        chunks.append({
            "start": start,
            "end": end,
            "text": text[start:end],
        })

        if end >= length:
            break

        start = max(
            start + 1,
            end - OVERLAP_SIZE,
        )

    return chunks



def filter_false_positives(results, text):
    """Remove known false-positive detections."""

    filtered = []

    relative_dates = {
        "today",
        "tomorrow",
        "yesterday",
    }

    field_labels = {
        "name",
        "email",
        "email address",
        "phone",
        "phone number",
        "credit card",
        "credit card number",
        "ip address",
        "employee id",
        "student id",
        "date of birth",
        "website",
    }

    for result in results:
        detected_text = text[
            result.start:result.end
        ].strip().lower()

        following_text = text[result.end:]
        preceding_text = text[:result.start]

        if (
            result.entity_type in {
                "PERSON", "ORGANIZATION", "LOCATION"
            }
            and detected_text in field_labels
            and re.match(r"\s*:", following_text)
        ):
            continue

        if (
            result.entity_type == "PERSON"
            and detected_text == "email"
        ):
            continue

        if (
            result.entity_type == "ORGANIZATION"
            and detected_text == "api"
        ):
            continue

        if (
            result.entity_type == "LOCATION"
            and detected_text == "ai"
            and re.search(
                r"\bPrivacyLens\s+$",
                preceding_text,
                re.IGNORECASE,
            )
        ):
            continue

        if (
            result.entity_type == "ORGANIZATION"
            and detected_text == "reach"
            and re.match(
                r"\s+[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
                following_text,
            )
        ):
            continue

        if (
            result.entity_type == "DATE_TIME"
            and detected_text in relative_dates
        ):
            continue

        if (
            result.entity_type == "LOCATION"
            and detected_text == "contact"
        ):
            continue

        filtered.append(result)

    return filtered


def resolve_phone_conflicts(results, text):
    """
    Prefer a US-formatted PHONE_NUMBER detection
    over a UK_NHS detection for the exact same span.

    Keep other UK_NHS detections unchanged.
    """

    us_phone_regex = re.compile(
        r"(?:\+1[\s.-]?)?"
        r"(?:\([2-9]\d{2}\)|[2-9]\d{2})"
        r"[\s.-]?"
        r"[2-9]\d{2}"
        r"[\s.-]?"
        r"\d{4}"
    )

    phone_spans = {
        (result.start, result.end)
        for result in results
        if (
            result.entity_type == "PHONE_NUMBER"
            and us_phone_regex.fullmatch(
                text[result.start:result.end]
            )
        )
    }

    resolved = [
        result
        for result in results
        if not (
            result.entity_type == "UK_NHS"
            and (result.start, result.end)
            in phone_spans
        )
    ]

    return resolved


def analyze_large_text(text):
    """
    Analyze text in chunks and return
    non-overlapping sensitive-data detections.
    """
    validate_text(text)

    chunks = create_chunks(text)
    candidates = []

    from presidio_analyzer import RecognizerResult

    id_regex = re.compile(
        r"\b(?:Student|Employee)\s+ID"
        r"\s*[:#-]\s*"
        r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b",
        re.IGNORECASE,
    )

    for match in id_regex.finditer(text):
        value = match.group(1)

        if 6 <= len(value) <= 32 and any(
            char.isdigit() for char in value
        ):
            candidates.append(
                RecognizerResult(
                    entity_type="CUSTOM_ID",
                    start=match.start(1),
                    end=match.end(1),
                    score=0.99,
                )
            )

    for chunk in chunks:
        local_results = analyzer.analyze(
            text=chunk["text"],
            language="en",
        )

        for result in local_results:
            global_start = (
                chunk["start"] + result.start
            )
            global_end = (
                chunk["start"] + result.end
            )

            if not (
                0 <= global_start
                < global_end
                <= len(text)
            ):
                continue

            result.start = global_start
            result.end = global_end

            candidates.append(result)

    # Prioritize high-confidence complete addresses.
    address_results = [
        result
        for result in candidates
        if (
            result.entity_type == "LOCATION"
            and result.score >= 0.90
            and any(
                char.isdigit()
                for char in text[
                    result.start:result.end
                ]
            )
        )
    ]

    other_results = [
        result
        for result in candidates
        if result not in address_results
    ]

    selected = list(address_results)

    for result in other_results:
        overlaps_address = any(
            result.start < address.end
            and result.end > address.start
            for address in address_results
        )

        if not overlaps_address:
            selected.append(result)

    # IMPORTANT: Resolve phone conflicts BEFORE
    # removing overlapping detections.
    selected = resolve_phone_conflicts(
        selected,
        text,
    )

    # Remove overlapping and duplicate detections.
    filtered = remove_overlapping_detections(
        selected
    )

    # Remove known false positives.
    filtered = filter_false_positives(
        filtered,
        text,
    )

    return filtered, len(chunks)
