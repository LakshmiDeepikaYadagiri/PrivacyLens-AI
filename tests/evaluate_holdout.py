
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from backend.chunk_processor import analyze_large_text


# New synthetic examples not used in the
# previous 50-sample evaluation.
#
# Each expected item is:
# (entity_type, exact matching text)

SAMPLES = [
    ("Email maria87@sample.net",
     [("EMAIL_ADDRESS", "maria87@sample.net")]),

    ("Reach support77@demo.org",
     [("EMAIL_ADDRESS", "support77@demo.org")]),

    ("Write to contact19@example.net",
     [("EMAIL_ADDRESS", "contact19@example.net")]),

    ("Email hr42@sample.org",
     [("EMAIL_ADDRESS", "hr42@sample.org")]),

    ("Send to billing8@demo.net",
     [("EMAIL_ADDRESS", "billing8@demo.net")]),

    ("Phone: 469-555-0142",
     [("PHONE_NUMBER", "469-555-0142")]),

    ("Call (702) 555-0163",
     [("PHONE_NUMBER", "(702) 555-0163")]),

    ("Mobile +1 512-555-0186",
     [("PHONE_NUMBER", "+1 512-555-0186")]),

    ("Number 408 555 0132",
     [("PHONE_NUMBER", "408 555 0132")]),

    ("Telephone 917-555-0174",
     [("PHONE_NUMBER", "917-555-0174")]),

    ("Student ID: GH456789",
     [("CUSTOM_ID", "Student ID: GH456789")]),

    ("Employee ID: EMP34567",
     [("CUSTOM_ID", "Employee ID: EMP34567")]),

    ("Student ID: AB765432",
     [("CUSTOM_ID", "Student ID: AB765432")]),

    ("Employee ID: WRK98765",
     [("CUSTOM_ID", "Employee ID: WRK98765")]),

    ("Student ID: STU45678",
     [("CUSTOM_ID", "Student ID: STU45678")]),

    ("Send to 5824 Willow Street, Denver, CO",
     [("LOCATION", "5824 Willow Street, Denver, CO")]),

    ("Address: 1742 Oak Avenue, Phoenix, AZ",
     [("LOCATION", "1742 Oak Avenue, Phoenix, AZ")]),

    ("Ship to 3658 Maple Drive, Orlando, FL",
     [("LOCATION", "3658 Maple Drive, Orlando, FL")]),

    ("Visit 7291 Birch Road, Houston, TX",
     [("LOCATION", "7291 Birch Road, Houston, TX")]),

    ("Deliver to 4826 Pine Lane, Seattle, WA",
     [("LOCATION", "4826 Pine Lane, Seattle, WA")]),

    ("The application completed successfully.", []),

    ("No sensitive information is included.", []),

    ("The database query returned five rows.", []),

    ("The dashboard is working correctly.", []),

    ("The report was generated successfully.", []),

    ("Email sara88@demo.org and call 214-555-0183",
     [
         ("EMAIL_ADDRESS", "sara88@demo.org"),
         ("PHONE_NUMBER", "214-555-0183"),
     ]),

    ("Student ID: XY654321, email user55@sample.net",
     [
         ("CUSTOM_ID", "Student ID: XY654321"),
         ("EMAIL_ADDRESS", "user55@sample.net"),
     ]),

    ("Call 646-555-0137 or 305-555-0192",
     [
         ("PHONE_NUMBER", "646-555-0137"),
         ("PHONE_NUMBER", "305-555-0192"),
     ]),

    ("Send to 2461 Elm Street, Dallas, TX. "
     "Email info72@demo.org",
     [
         ("LOCATION", "2461 Elm Street, Dallas, TX"),
         ("EMAIL_ADDRESS", "info72@demo.org"),
     ]),

    ("Employee ID: EMP24680, phone (832) 555-0149",
     [
         ("CUSTOM_ID", "Employee ID: EMP24680"),
         ("PHONE_NUMBER", "(832) 555-0149"),
     ]),
]


def expected_entities(text, labels):
    """
    Convert expected labels to exact offsets.

    Handles repeated identical entities by
    matching successive occurrences.
    """
    entities = []
    next_positions = {}

    for entity_type, value in labels:
        key = (entity_type, value)

        search_from = next_positions.get(key, 0)
        start = text.find(value, search_from)

        if start == -1:
            raise ValueError(
                f"Expected value not found: {value}"
            )

        end = start + len(value)
        next_positions[key] = end

        entities.append(
            (entity_type, start, end)
        )

    return entities


def evaluate():
    total_tp = 0
    total_fp = 0
    total_fn = 0
    passed_samples = 0
    details = []

    for index, (text, labels) in enumerate(
        SAMPLES, start=1
    ):
        expected = Counter(
            expected_entities(text, labels)
        )

        results, _ = analyze_large_text(text)

        predicted = Counter(
            (
                result.entity_type,
                result.start,
                result.end,
            )
            for result in results
        )

        true_matches = expected & predicted

        false_matches = predicted - expected
        missed_matches = expected - predicted

        tp = sum(true_matches.values())
        fp = sum(false_matches.values())
        fn = sum(missed_matches.values())

        total_tp += tp
        total_fp += fp
        total_fn += fn

        passed = (
            fp == 0 and fn == 0
        )

        if passed:
            passed_samples += 1

        print(
            f"Sample {index}: "
            f"{'PASS' if passed else 'CHECK'}"
        )

        if not passed:
            for entity_type, start, end in (
                false_matches.elements()
            ):
                print(
                    "  Extra:",
                    entity_type,
                    repr(text[start:end]),
                )

            for entity_type, start, end in (
                missed_matches.elements()
            ):
                print(
                    "  Missed:",
                    entity_type,
                    repr(text[start:end]),
                )

        details.append({
            "sample": index,
            "text": text,
            "passed": passed,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        })

    precision = (
        total_tp / (total_tp + total_fp)
        if total_tp + total_fp else 0.0
    )

    recall = (
        total_tp / (total_tp + total_fn)
        if total_tp + total_fn else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall else 0.0
    )

    report = {
        "evaluation_type": "synthetic_holdout",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "samples": len(SAMPLES),
        "passed_samples": passed_samples,
        "true_positives": total_tp,
        "false_positives": total_fp,
        "false_negatives": total_fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "details": details,
    }

    output_dir = Path("evaluation_reports")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir / "holdout_evaluation.json"
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 50)
    print("PRIVACYLENS AI - FRESH EVALUATION")
    print("=" * 50)

    print("Samples:", len(SAMPLES))
    print("Passed Samples:", passed_samples)
    print("True Positives:", total_tp)
    print("False Positives:", total_fp)
    print("False Negatives:", total_fn)

    print(
        f"Precision: {precision * 100:.2f}%"
    )
    print(
        f"Recall: {recall * 100:.2f}%"
    )
    print(
        f"F1 Score: {f1 * 100:.2f}%"
    )

    print("Report saved:", output_path)
    print("=" * 50)


if __name__ == "__main__":
    evaluate()
