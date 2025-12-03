import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'latest'))
from translator.nlp import process
from translator.translator import translate_sentence

def check_issues():
    sentences = [
        "All whales are mammals",
        "Alice is a whale",
        "Alice is a mammal"
    ]
    
    print(f"{'Sentence':<30} | {'POS Tags'}")
    print("-" * 80)
    
    for sent in sentences:
        doc = process(sent)
        tags = " ".join([f"{t.text}:{t.pos_}({t.lemma_})" for t in doc])
        print(f"{sent:<30} | {tags}")
        
    print("\nTranslations:")
    print("-" * 80)
    for sent in sentences:
        try:
            fol = translate_sentence(sent)
            print(f"{sent:<30} | {fol}")
        except Exception as e:
            print(f"{sent:<30} | ERROR: {e}")

if __name__ == "__main__":
    check_issues()
