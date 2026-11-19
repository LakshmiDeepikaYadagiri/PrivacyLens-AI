
from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerRegistry,
    Pattern,
    PatternRecognizer,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider


# ----------------------------------------
# 1. Load spaCy English model
# ----------------------------------------

configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {
            "lang_code": "en",
            "model_name": "en_core_web_sm",
        }
    ],
}

provider = NlpEngineProvider(
    nlp_configuration=configuration
)

nlp_engine = provider.create_engine()


# ----------------------------------------
# 2. Load Presidio built-in recognizers
# ----------------------------------------

registry = RecognizerRegistry()

registry.load_predefined_recognizers(
    nlp_engine=nlp_engine
)


# ----------------------------------------
# 3. Custom student/employee ID recognizer
# ----------------------------------------

id_pattern = Pattern(
    name="labeled_id_pattern",
    regex=(
        r"\b(?:Student|Employee)\s+ID"
        r"\s*[:#-]\s*[A-Za-z0-9]{6,12}\b"
    ),
    score=0.85,
)

id_recognizer = PatternRecognizer(
    supported_entity="CUSTOM_ID",
    patterns=[id_pattern],
    supported_language="en",
    name="LabeledIDRecognizer",
)

registry.add_recognizer(id_recognizer)


# ----------------------------------------
# 4. Custom US street address recognizer
# ----------------------------------------

address_pattern = Pattern(
    name="us_street_address",
    regex=(
        r"\b\d{1,6}\s+"
        r"(?:[A-Za-z0-9]+\s+){1,5}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|"
        r"Drive|Dr|Lane|Ln|Boulevard|Blvd)"
        r"\.?,\s*"
        r"[A-Za-z]+(?:\s+[A-Za-z]+)*"
        r",\s*[A-Z]{2}\b"
    ),
    score=0.90,
)

address_recognizer = PatternRecognizer(
    supported_entity="LOCATION",
    patterns=[address_pattern],
    supported_language="en",
    name="USStreetAddressRecognizer",
)

registry.add_recognizer(address_recognizer)


# ----------------------------------------
# 5. Custom US phone-number recognizer
# ----------------------------------------

# Recognizes common US formats:
#
# 617-555-0129
# (617) 555-0129
# 617 555 0129
# +1 617-555-0129
#
# This is format recognition, not proof
# that a number is assigned or reachable.

us_phone_pattern = Pattern(
    name="us_phone_number",
    regex=(
        r"(?<![\w+])"
        r"(?:\+1[\s.-]?)?"
        r"(?:"
        r"\([2-9]\d{2}\)"
        r"|"
        r"[2-9]\d{2}"
        r")"
        r"[\s.-]?"
        r"[2-9]\d{2}"
        r"[\s.-]?"
        r"\d{4}"
        r"(?!\w)"
    ),
    score=0.95,
)

us_phone_recognizer = PatternRecognizer(
    supported_entity="PHONE_NUMBER",
    patterns=[us_phone_pattern],
    supported_language="en",
    name="USPhoneNumberRecognizer",
)

registry.add_recognizer(us_phone_recognizer)


# ----------------------------------------
# 6. Create analyzer
# ----------------------------------------

analyzer = AnalyzerEngine(
    registry=registry,
    nlp_engine=nlp_engine,
    supported_languages=["en"],
)
