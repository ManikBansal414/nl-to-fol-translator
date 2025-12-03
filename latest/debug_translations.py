import sys
import os

# Add the current directory to sys.path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'latest'))

from translator.translator import translate_sentence

def debug_translations():
    sentences = [
        # Universal entailment simple
        "All humans are mortal",
        "Socrates is a human",
        "Socrates is mortal",
        
        # Transitivity with chaining
        "All A are B",
        "All B are C",
        "x is A",
        "x is C",
        
        # Negation inference
        "No humans are immortal",
        "Socrates is not immortal",
        
        # Relative clause entailment
        "Every person who is rich is happy",
        "Alice is a person",
        "Alice is rich",
        "Alice is happy",
        
        # Not-all pattern
        "Not all birds are white",
        "There is a bird",
        
        # No <NOUN> <VERB>
        "No fish walk",
        "Nemo is a fish",
        "Nemo walks",
        "Nemo does not walk",
        
        # Universal verb pattern
        "Every student reads a book",
        "Bob is a student",
        "Bob reads a book"
    ]
    
    print(f"{'Sentence':<40} | {'FOL Translation'}")
    print("-" * 80)
    
    for sent in sentences:
        try:
            fol = translate_sentence(sent)
            print(f"{sent:<40} | {fol}")
        except Exception as e:
            print(f"{sent:<40} | ERROR: {e}")

if __name__ == "__main__":
    debug_translations()
