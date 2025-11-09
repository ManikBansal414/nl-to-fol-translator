"""spaCy wrapper for tokenization and linguistic annotations."""
import spacy

nlp = spacy.load("en_core_web_sm")  # Loaded once per process

def process(text):
    """Return spaCy Doc for input text."""
    return nlp(text)
