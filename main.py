#!/usr/bin/env python
"""Unified entry point.
Usage:
  python main.py --method lark "All humans are mortal"
  python main.py --method nltk "If Some daisies are flowers then All daisies are flowers"
  python main.py --method fomaster "All humans are mortal"
  python main.py --all "Some dogs are friendly"
"""
from __future__ import annotations
import argparse

from translator import translate_sentence
from method_lark.validator import validate as validate_lark
from method_nltk.validator import validate as validate_nltk
from method_fomaster.validator import validate as validate_fomaster


METHODS = {
    "lark": lambda fol: validate_lark(fol),
    "nltk": lambda fol: validate_nltk(fol),
    "fomaster": lambda fol: validate_fomaster(fol),
}


def run(sentence: str, method: str | None, all_methods: bool):
    fol = translate_sentence(sentence)
    if fol.startswith("[ERROR]"):
        print(f"NL: {sentence}\nERROR: {fol}\n")
        return
    print(f"NL: {sentence}")
    print(f"FOL: {fol}")
    if all_methods:
        for name, fn in METHODS.items():
            print(f"  {name}: {fn(fol)}")
    else:
        fn = METHODS.get(method or "")
        if fn is None:
            print(f"Unknown method: {method}")
        else:
            print(f"Valid ({method}): {fn(fol)}")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Common NL→FOL translator with multiple validators."
    )
    ap.add_argument("sentence", nargs="+", help="Input sentence(s)")
    ap.add_argument(
        "--method", choices=METHODS.keys(), help="Single method to validate"
    )
    ap.add_argument("--all", action="store_true", help="Run all methods")
    args = ap.parse_args()
    for s in args.sentence:
        run(s, args.method, args.all)


if __name__ == "__main__":
    main()
