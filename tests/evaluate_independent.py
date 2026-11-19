
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from backend.chunk_processor import analyze_large_text


# Independent synthetic evaluation dataset.
#
# Each expected annotation is:
# (entity_type, exact_text)
#
# These examples have not been used to tune
# the detector in the previous evaluations.

DATASET = [
    # 1-8: Email addresses
    ("Please email sarah.lee@example.com",
     [("EMAIL_ADDRESS", "sarah.lee@example.com")]),

    ("Contact admin42@example.org",
     [("EMAIL_ADDRESS", "admin42@example.org")]),

    ("Send updates to first.last@example.net",
     [("EMAIL_ADDRESS", "first.last@example.net")]),

    ("My address is helpdesk@example.com",
     [("EMAIL_ADDRESS", "helpdesk@example.com")]),

    ("Write to user_name@example.org",
     [("EMAIL_ADDRESS", "user_name@example.org")]),

    ("The contact is billing.team@example.com",
     [("EMAIL_ADDRESS", "billing.team@example.com")]),

    ("Use test123@example.net",
     [("EMAIL_ADDRESS", "test123@example.net")]),

    ("Email security.alerts@example.org",
     [("EMAIL_ADDRESS", "security.alerts@example.org")]),

    # 9-16: Phone numbers
    ("Call 312-555-0184",
     [("PHONE_NUMBER", "312-555-0184")]),

    ("My number is 617-555-0129",
     [("PHONE_NUMBER", "617-555-0129")]),

    ("Phone: (404) 555-0173",
     [("PHONE_NUMBER", "(404) 555-0173")]),

    ("Reach us at +1 512-555-0194",
     [("PHONE_NUMBER", "+1 512-555-0194")]),

    ("Call 206-555-0158",
     [("PHONE_NUMBER", "206-555-0158")]),

    ("My contact number is 713-555-0146",
     [("PHONE_NUMBER", "713-555-0146")]),

    ("Telephone: 305-555-0117",
     [("PHONE_NUMBER", "305-555-0117")]),

    ("Reach me on 919-555-0162",
     [("PHONE_NUMBER", "919-555-0162")]),

    # 17-22: Custom identifiers
    ("Student ID: JK765432",
     [("CUSTOM_ID", "Student ID: JK765432")]),

    ("Employee ID: EMP45678",
     [("CUSTOM_ID", "Employee ID: EMP45678")]),

    ("Student ID: LM234567",
     [("CUSTOM_ID", "Student ID: LM234567")]),

    ("Employee ID: STAFF456",
     [("CUSTOM_ID", "Employee ID: STAFF456")]),

    ("Student ID: NP876543",
     [("CUSTOM_ID", "Student ID: NP876543")]),

    ("Employee ID: EMP65432",
     [("CUSTOM_ID", "Employee ID: EMP65432")]),

    # 23-28: Names
    ("Please meet Rebecca Martinez",
     [("PERSON", "Rebecca Martinez")]),

    ("I spoke with Christopher Harris",
     [("PERSON", "Christopher Harris")]),

    ("The applicant is Amanda Wilson",
     [("PERSON", "Amanda Wilson")]),

    ("Contact Daniel Thompson",
     [("PERSON", "Daniel Thompson")]),

    ("The manager is Olivia Robinson",
     [("PERSON", "Olivia Robinson")]),

    ("The customer is Benjamin Carter",
     [("PERSON", "Benjamin Carter")]),

    # 29-34: Street addresses
    ("Deliver to 812 Cedar Street, Seattle, WA",
     [("LOCATION", "812 Cedar Street, Seattle, WA")]),

    ("Ship to 427 Birch Avenue, Portland, OR",
     [("LOCATION", "427 Birch Avenue, Portland, OR")]),

    ("Visit 936 Walnut Road, Chicago, IL",
     [("LOCATION", "936 Walnut Road, Chicago, IL")]),

    ("My office is at 215 River Drive, Miami, FL",
     [("LOCATION", "215 River Drive, Miami, FL")]),

    ("Send mail to 583 Sunset Lane, Boston, MA",
     [("LOCATION", "583 Sunset Lane, Boston, MA")]),

    ("Find us at 764 Forest Boulevard, Atlanta, GA",
     [("LOCATION", "764 Forest Boulevard, Atlanta, GA")]),

    # 35-38: Explicit dates
    ("Born on February 18, 1997",
     [("DATE_TIME", "February 18, 1997")]),

    ("Appointment: September 14, 2027",
     [("DATE_TIME", "September 14, 2027")]),

    ("The event is on April 22, 2028",
     [("DATE_TIME", "April 22, 2028")]),

    ("The document is dated November 9, 2026",
     [("DATE_TIME", "November 9, 2026")]),

    # 39-44: Non-sensitive examples
    ("The server restarted successfully.", []),

    ("We updated the privacy dashboard.", []),

    ("The software processes uploaded files.", []),

    ("Please verify the configuration.", []),

    ("The API request completed successfully.", []),

    ("The database query returned results.", []),

    # 45-50: Multiple entities and edge cases
    (
        "Contact emily.chen@example.com or "
        "call 469-555-0138",
        [
            ("EMAIL_ADDRESS", "emily.chen@example.com"),
            ("PHONE_NUMBER", "469-555-0138"),
        ],
    ),

    (
        "Student ID: QR345678 belongs to "
        "Nathan Brooks",
        [
            ("CUSTOM_ID", "Student ID: QR345678"),
            ("PERSON", "Nathan Brooks"),
        ],
    ),

    (
        "Employee ID: EMP24680, email "
        "jordan@example.net",
        [
            ("CUSTOM_ID", "Employee ID: EMP24680"),
            ("EMAIL_ADDRESS", "jordan@example.net"),
        ],
    ),

    (
        "Send to 345 Harbor Road, Tampa, FL "
        "and email shipping@example.com",
        [
            ("LOCATION", "345 Harbor Road, Tampa, FL"),
            ("EMAIL_ADDRESS", "shipping@example.com"),
        ],
    ),

    (
        "Call (214) 555-0196 or email "
        "team@example.org",
        [
            ("PHONE_NUMBER", "(214) 555-0196"),
            ("EMAIL_ADDRESS", "team@example.org"),
        ],
    ),

    (
        "The applicant is Sophia Mitchell, "
        "Student ID: ST567890",
        [
            ("PERSON", "Sophia Mitchell"),
            ("CUSTOM_ID", "Student ID: ST567890"),
        ],
    ),
]


def expected_spans(text, labels):
    """
    Convert expected text annotations into
    exact character positions.

    Raise an error if an annotation is missing
    or appears more than once.
    """
    spans = set()

    for entity_type, value in labels:
        start = text.find(value)

        if start == -1:
            raise ValueError(
                f"Annotation not found: {value!r}"
            )

        if text.find(value, start + 1) != -1:
            raise ValueError(
                f"Ambiguous annotation: {value!r}"
            )

        spans.add(
            (entity_type, start, start + len(value))
        )

    return spans


def format_spans(text, spans):
    return [
        {
            "entity_type": entity,
            "text": text[start:end],
            "start": start,
            "end": end,
        }
        for entity, start, end in sorted(spans)
    ]


def evaluate():
    tp = 0
    fp = 0
    fn = 0

    passed_samples = 0
    failed_samples = 0
    errors = []

    print("=" * 55)
    print("PRIVACYLENS AI - INDEPENDENT EVALUATION")
    print("=" * 55)

    for index, (text, labels) in enumerate(
        DATASET, start=1
    ):
        expected = expected_spans(text, labels)

        results, _ = analyze_large_text(text)

        predicted = {
            (
                result.entity_type,
                result.start,
                result.end,
            )
            for result in results
        }

        correct = predicted & expected
        extra = predicted - expected
        missed = expected - predicted

        tp += len(correct)
        fp += len(extra)
        fn += len(missed)

        if not extra and not missed:
            status = "PASS"
            passed_samples += 1
        else:
            status = "CHECK"
            failed_samples += 1

            errors.append({
                "sample": index,
                "text": text,
                "extra": format_spans(text, extra),
                "missed": format_spans(text, missed),
            })

        print(f"\nSample {index}: {status}")

        if extra:
            print("  Extra detections:")
            for item in format_spans(text, extra):
                print(
                    f"    {item['entity_type']}: "
                    f"{item['text']!r}"
                )

        if missed:
            print("  Missed detections:")
            for item in format_spans(text, missed):
                print(
                    f"    {item['entity_type']}: "
                    f"{item['text']!r}"
                )

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    report = {
        "evaluation": "independent_synthetic",
        "timestamp": datetime.now().isoformat(),
        "samples": len(DATASET),
        "passed_samples": passed_samples,
        "failed_samples": failed_samples,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "errors": errors,
    }

    report_dir = Path("evaluation_reports")
    report_dir.mkdir(exist_ok=True)

    report_path = (
        report_dir / "independent_evaluation.json"
    )

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("FINAL RESULTS")
    print("=" * 55)
    print(f"Samples:         {len(DATASET)}")
    print(f"Passed Samples:  {passed_samples}")
    print(f"Check Samples:   {failed_samples}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"Precision:       {precision:.2%}")
    print(f"Recall:          {recall:.2%}")
    print(f"F1 Score:        {f1:.2%}")
    print(f"Report saved:    {report_path}")
    print("=" * 55)


if __name__ == "__main__":
    evaluate()
