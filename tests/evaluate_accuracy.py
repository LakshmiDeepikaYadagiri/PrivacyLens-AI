
from backend.chunk_processor import analyze_large_text


# Synthetic evaluation dataset.
# Each expected item is (entity_type, exact_text).
dataset = [
    {
        "text": "Contact john@example.com",
        "expected": [
            ("EMAIL_ADDRESS", "john@example.com")
        ],
    },
    {
        "text": "Email me at alice@example.org",
        "expected": [
            ("EMAIL_ADDRESS", "alice@example.org")
        ],
    },
    {
        "text": "Student ID: AB123456",
        "expected": [
            ("CUSTOM_ID", "Student ID: AB123456")
        ],
    },
    {
        "text": "Employee ID: EMP98765",
        "expected": [
            ("CUSTOM_ID", "Employee ID: EMP98765")
        ],
    },
    {
        "text": "The meeting is scheduled for tomorrow.",
        "expected": [],
    },
]


def evaluate():
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for index, sample in enumerate(dataset, start=1):
        text = sample["text"]

        results, _ = analyze_large_text(text)

        predicted = {
            (
                result.entity_type,
                text[result.start:result.end],
            )
            for result in results
        }

        expected = set(sample["expected"])

        tp = len(predicted & expected)
        fp = len(predicted - expected)
        fn = len(expected - predicted)

        true_positives += tp
        false_positives += fp
        false_negatives += fn

        print(f"\nSample {index}")
        print(f"Text: {text}")
        print(f"Expected: {expected}")
        print(f"Predicted: {predicted}")
        print(f"TP={tp}, FP={fp}, FN={fn}")

    precision = (
        true_positives /
        (true_positives + false_positives)
        if true_positives + false_positives
        else 0
    )

    recall = (
        true_positives /
        (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    print("\n" + "=" * 40)
    print("PRIVACYLENS AI - DETECTION EVALUATION")
    print("=" * 40)
    print(f"True Positives:  {true_positives}")
    print(f"False Positives: {false_positives}")
    print(f"False Negatives: {false_negatives}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"F1 Score:  {f1:.2%}")
    print("=" * 40)


if __name__ == "__main__":
    evaluate()
