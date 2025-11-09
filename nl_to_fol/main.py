from parser.pipeline import translate_sentence
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py \"sentence here\"")
        exit()

    sentence = " ".join(sys.argv[1:])
    result = translate_sentence(sentence)
    print("Input: ", sentence)
    print("Output:", result)
