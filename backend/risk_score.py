
from backend.chunk_processor import analyze_large_text

# Heuristic privacy-risk weights.
RISK_WEIGHTS = {
    "US_SSN": 30,
    "CREDIT_CARD": 30,
    "US_BANK_NUMBER": 25,
    "EMAIL_ADDRESS": 10,
    "PHONE_NUMBER": 10,
    "PERSON": 5,
    "LOCATION": 5,
    "IP_ADDRESS": 5,
    "URL": 2,
}


def calculate_risk(text):
    results, total_chunks = analyze_large_text(text)

    score = sum(
        RISK_WEIGHTS.get(result.entity_type, 5)
        for result in results
    )

    # Keep the score between 0 and 100.
    score = min(score, 100)

    if score >= 70:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    return {
        "risk_score": score,
        "risk_level": level,
        "total_detected": len(results),
        "total_chunks": total_chunks,
    }
