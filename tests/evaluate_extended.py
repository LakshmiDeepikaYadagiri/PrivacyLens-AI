
from backend.chunk_processor import analyze_large_text

# Synthetic examples for an independent evaluation.
# Expected labels are (entity type, exact text).
# These examples were not used in the initial five-sample test.

DATASET = [
    # Emails
    ("Reach us at support@example.com",
     [("EMAIL_ADDRESS", "support@example.com")]),
    ("Send the file to maria.smith@example.org",
     [("EMAIL_ADDRESS", "maria.smith@example.org")]),
    ("My email is alex99@example.net",
     [("EMAIL_ADDRESS", "alex99@example.net")]),
    ("Contact billing@example.com for help",
     [("EMAIL_ADDRESS", "billing@example.com")]),
    ("Write to info@example.org",
     [("EMAIL_ADDRESS", "info@example.org")]),

    # Phone numbers
    ("Call me at 212-555-0147",
     [("PHONE_NUMBER", "212-555-0147")]),
    ("My phone is 415-555-0198",
     [("PHONE_NUMBER", "415-555-0198")]),
    ("Reach me at (202) 555-0164",
     [("PHONE_NUMBER", "(202) 555-0164")]),
    ("Call +1 303-555-0125",
     [("PHONE_NUMBER", "+1 303-555-0125")]),
    ("Phone: 646-555-0182",
     [("PHONE_NUMBER", "646-555-0182")]),

    # Custom IDs
    ("Student ID: XY654321",
     [("CUSTOM_ID", "Student ID: XY654321")]),
    ("Employee ID: EMP12345",
     [("CUSTOM_ID", "Employee ID: EMP12345")]),
    ("Student ID: CD987654",
     [("CUSTOM_ID", "Student ID: CD987654")]),
    ("Employee ID: STAFF789",
     [("CUSTOM_ID", "Employee ID: STAFF789")]),
    ("Student ID: GH456789",
     [("CUSTOM_ID", "Student ID: GH456789")]),

    # Names
    ("My name is Jennifer Williams",
     [("PERSON", "Jennifer Williams")]),
    ("I spoke with Michael Johnson",
     [("PERSON", "Michael Johnson")]),
    ("The customer is Patricia Brown",
     [("PERSON", "Patricia Brown")]),
    ("Please contact Robert Anderson",
     [("PERSON", "Robert Anderson")]),
    ("The employee is Elizabeth Taylor",
     [("PERSON", "Elizabeth Taylor")]),

    # Dates
    ("My birthday is January 15, 1998",
     [("DATE_TIME", "January 15, 1998")]),
    ("The appointment is on March 20, 2027",
     [("DATE_TIME", "March 20, 2027")]),
    ("The meeting was held on June 12, 2025",
     [("DATE_TIME", "June 12, 2025")]),
    ("The report is dated August 5, 2026",
     [("DATE_TIME", "August 5, 2026")]),
    ("The deadline is December 10, 2027",
     [("DATE_TIME", "December 10, 2027")]),

    # Addresses
    ("I live at 123 Main Street, Dallas, TX",
     [("LOCATION", "123 Main Street, Dallas, TX")]),
    ("Deliver to 456 Oak Avenue, Austin, TX",
     [("LOCATION", "456 Oak Avenue, Austin, TX")]),
    ("The office is at 789 Pine Road, Denver, CO",
     [("LOCATION", "789 Pine Road, Denver, CO")]),
    ("Ship to 321 Elm Street, Houston, TX",
     [("LOCATION", "321 Elm Street, Houston, TX")]),
    ("Visit 654 Maple Drive, Phoenix, AZ",
     [("LOCATION", "654 Maple Drive, Phoenix, AZ")]),

    # Non-sensitive examples under our evaluation policy
    ("The application is running correctly.", []),
    ("We completed the project successfully.", []),
    ("Please review the latest documentation.", []),
    ("The dashboard displays the results.", []),
    ("The system processes large documents.", []),
    ("Our team discussed the next release.", []),
    ("The API returned a successful response.", []),
    ("The database connection is working.", []),
    ("The application supports file uploads.", []),
    ("The testing process is complete.", []),
]


def find_expected_spans(text, labels):
    """
    Convert expected entity strings to exact character
    spans. Reject ambiguous or missing annotations.
    """
    expected = set()

    for entity_type, value in labels:
        start = text.find(value)

        if start == -1:
            raise ValueError(
                f"Missing annotation: {value!r}"
            )

        if text.find(value, start + 1) != -1:
            raise ValueError(
                f"Ambiguous annotation: {value!r}"
            )

        expected.add(
            (entity_type, start, start + len(value))
        )

    return expected


def evaluate():
    tp = 0
    fp = 0
    fn = 0

    print("=" * 55)
    print("PRIVACYLENS AI - EXTENDED EVALUATION")
    print("=" * 55)

    for index, (text, labels) in enumerate(
        DATASET, start=1
    ):
        results, _ = analyze_large_text(text)

        predicted = {
            (
                result.entity_type,
                result.start,
                result.end,
            )
            for result in results
        }

        expected = find_expected_spans(
            text, labels
        )

        correct = predicted & expected
        extra = predicted - expected
        missed = expected - predicted

        tp += len(correct)
        fp += len(extra)
        fn += len(missed)

        status = (
            "PASS"
            if not extra and not missed
            else "CHECK"
        )

        print(f"\nSample {index}: {status}")
        print(f"Text: {text}")

        if extra:
            print("Extra detections:")
            for entity, start, end in sorted(extra):
                print(
                    f"  {entity}: {text[start:end]!r}"
                )

        if missed:
            print("Missed detections:")
            for entity, start, end in sorted(missed):
                print(
                    f"  {entity}: {text[start:end]!r}"
                )

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    print("\n" + "=" * 55)
    print("FINAL RESULTS")
    print("=" * 55)
    print(f"Samples:         {len(DATASET)}")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"Precision:       {precision:.2%}")
    print(f"Recall:          {recall:.2%}")
    print(f"F1 Score:        {f1:.2%}")
    print("=" * 55)


if __name__ == "__main__":
    evaluate()
