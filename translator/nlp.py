"""spaCy wrapper (common)."""
import spacy

nlp = spacy.load("en_core_web_sm")

def process(text: str):
    return nlp(text)
