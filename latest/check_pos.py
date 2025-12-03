import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'latest'))
from translator.nlp import process

def check_pos():
    sentences = [
        "All A are B",
        "x is A",
        "x is C"
    ]
    
    for sent in sentences:
        doc = process(sent)
        print(f"Sentence: {sent}")
        for token in doc:
            print(f"  {token.text}: {token.pos_} ({token.tag_})")

if __name__ == "__main__":
    check_pos()
