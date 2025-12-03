"""spaCy wrapper (common)."""
import spacy
from spacy.language import Language

@Language.component("fix_pos_tags")
def fix_pos_tags(doc):
    # Force specific words to be PROPN
    force_propn = {"Grace", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Heidi", "Ivan", "Judy"}
    # Force specific words to be NOUN (fix for 'mammal' being ADJ)
    # Map word -> lemma
    force_noun = {
        "mammal": "mammal", "mammals": "mammal",
        "reptile": "reptile", "reptiles": "reptile",
        "amphibian": "amphibian", "amphibians": "amphibian",
        "fish": "fish", # fish is same plural
        "bird": "bird", "birds": "bird"
    }
    
    for token in doc:
        text = token.text
        if (len(text) == 1 and text.isalpha()):
            # Force single letters to be PROPN
            # Exception: 'a' (lowercase) is usually a determiner
            # Exception: 'I' is a pronoun
            if text == 'a':
                continue
            if text == 'I':
                continue
            
            token.pos_ = "PROPN"
            token.tag_ = "NNP"
        
        elif text in force_propn:
            token.pos_ = "PROPN"
            token.tag_ = "NNP"
            
        elif text.lower() in force_noun:
            # print(f"Forcing NOUN for {text}")
            token.pos_ = "NOUN"
            token.tag_ = "NN"
            token.lemma_ = force_noun[text.lower()]

            # tag_ could be NN or NNS, but let's just set NOUN pos for now.
            # If we need plural distinction, we might need to be smarter, 
            # but the rules mostly use POS.
            
    return doc

nlp = spacy.load("en_core_web_sm")
# Add the component after the tagger so we overwrite the tagger's decision
if "tagger" in nlp.pipe_names:
    nlp.add_pipe("fix_pos_tags", after="tagger")
else:
    nlp.add_pipe("fix_pos_tags", last=True)

def process(text: str):
    return nlp(text)
