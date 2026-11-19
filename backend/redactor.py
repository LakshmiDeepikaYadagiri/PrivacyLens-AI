
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from backend.chunk_processor import analyze_large_text


anonymizer = AnonymizerEngine()


def redact_text(text):
    results, total_chunks = analyze_large_text(text)

    replacements = {
        "DEFAULT": "[REDACTED]",
        "PERSON": "[Name]",
        "EMAIL_ADDRESS": "[EMAIL_ADDRESS]",
        "PHONE_NUMBER": "[PHONE_NUMBER]",
        "LOCATION": "[LOCATION]",
        "US_SSN": "[US_SSN]",
        "CREDIT_CARD": "[CREDIT_CARD]",
        "US_BANK_NUMBER": "[US_BANK_NUMBER]",
        "IP_ADDRESS": "[IP_ADDRESS]",
        "URL": "[URL]",
        "CUSTOM_ID": "[CUSTOM_ID]",
        "DATE_TIME": "[DATE_TIME]",
    }

    operators = {
        entity: OperatorConfig(
            "replace",
            {"new_value": label},
        )
        for entity, label in replacements.items()
    }

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    return {
        "redacted_text": anonymized.text,
        "total_detected": len(results),
        "total_chunks": total_chunks,
    }
