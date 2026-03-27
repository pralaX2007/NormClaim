"""
NormClaim — NLP Extraction Pipeline
Handles clinical and financial entity extraction using spaCy and Gemini.
"""

import spacy
from medspacy.context import ConTextComponent
import json

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Add ConText for negation detection
context = ConTextComponent()
nlp.add_pipe(context, last=True)

# Placeholder for abbreviation map
ABBREV_MAP = {
    "c/o": "complaining of",
    "h/o": "history of",
    "k/c/o": "known case of",
    "TDS": "three times daily",
    "T.": "Tablet",
    "Inj.": "Injection",
}

def expand_abbreviations(text):
    """Expand abbreviations in the input text."""
    for abbr, full_form in ABBREV_MAP.items():
        text = text.replace(abbr, full_form)
    return text

def process_text(raw_text):
    """Process raw text through the NLP pipeline."""
    # Step 1: Expand abbreviations
    expanded_text = expand_abbreviations(raw_text)

    # Step 2: Run spaCy pipeline
    doc = nlp(expanded_text)

    # Step 3: Extract structured data
    sections = {}
    negated_spans = []

    for sent in doc.sents:
        # Example section detection (placeholder logic)
        if "C/O:" in sent.text:
            sections[sent.start] = "complaint"
        elif "H/O:" in sent.text:
            sections[sent.start] = "history"

        # Collect negated spans
        for ent in sent.ents:
            if ent._.is_negated:
                negated_spans.append(ent.text)

    return {
        "expanded_text": expanded_text,
        "sections": sections,
        "negated_spans": negated_spans,
    }

# Example usage
if __name__ == "__main__":
    sample_text = "Pt c/o Ghabrahat ++. No h/o TB. k/c/o DM, HTN."
    result = process_text(sample_text)
    print(json.dumps(result, indent=2))