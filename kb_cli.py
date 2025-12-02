#!/usr/bin/env python
"""
Robust CLI for the NL-to-FOL Knowledge Base.

Usage:
  # Add knowledge (Natural Language)
  python kb_cli.py add "All humans are mortal"
  python kb_cli.py add "Socrates is human"

  # Query knowledge (Natural Language)
  python kb_cli.py query "Is Socrates mortal?"
  python kb_cli.py query "Some humans are mortal"

  # Manage KB
  python kb_cli.py list
  python kb_cli.py clear
"""
from __future__ import annotations
import argparse
import sys
from translator import translate_sentence
from knowledge_base import kb


def cmd_add(sentence: str):
    print(f"Processing: '{sentence}'")
    # 1. Translate NL -> FOL
    fol = translate_sentence(sentence)
    if fol.startswith("[ERROR]"):
        print(f"❌ Translation Failed: {fol}")
        return

    print(f"   ↳ FOL: {fol}")

    # 2. Add to KB
    if kb().add(fol):
        print(f"✅ Added to Knowledge Base.")
    else:
        print(
            f"⚠️  Parsed valid FOL but KB could not process it (stored as raw formula)."
        )


def cmd_query(sentence: str):
    print(f"Querying: '{sentence}'")
    # 1. Translate NL -> FOL
    fol = translate_sentence(sentence)
    if fol.startswith("[ERROR]"):
        print(f"❌ Translation Failed: {fol}")
        return

    print(f"   ↳ FOL: {fol}")

    # 2. Ask KB
    entailed, trace = kb().query(fol)

    if entailed:
        print("✅ Result: TRUE (Entailed)")
        print("\n--- Proof Trace ---")
        for line in trace:
            print(f"  {line}")
        print("-------------------")
    else:
        print("❌ Result: FALSE (Not Entailed or Unknown)")
        if trace:
            print("\n--- Trace/Reason ---")
            for line in trace:
                print(f"  {line}")


def cmd_list():
    state = kb().get_state()

    print(f"\n📊 Knowledge Base Stats")
    print(f"   Facts: {state['stats']['fact_count']}")
    print(f"   Rules: {state['stats']['rule_count']}")
    print(f"   Active Predicates: {', '.join(state['stats']['active_predicates'])}")

    print("\n📝 Facts:")
    if not state["facts"]:
        print("   (none)")
    else:
        for f in state["facts"]:
            print(f"   - {f}")

    print("\n📜 Rules:")
    if not state["rules"]:
        print("   (none)")
    else:
        for r in state["rules"]:
            # The new KB returns rule strings directly, no need for tuple unpacking
            print(f"   - {r}")

    print("\n📂 Other Formulas (Stored but not Executed):")
    if not state["other"]:
        print("   (none)")
    else:
        for o in state["other"]:
            print(f"   - {o}")
    print()


def cmd_clear():
    kb().clear()
    print("🗑️  Knowledge Base cleared.")


def main():
    parser = argparse.ArgumentParser(description="NL-to-FOL Knowledge Base CLI")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # Add command
    p_add = subparsers.add_parser(
        "add", help="Add a Natural Language sentence to the KB"
    )
    p_add.add_argument(
        "sentence", nargs="+", help='The English sentence (e.g., "All men are mortal")'
    )

    # Query command
    p_query = subparsers.add_parser("query", help="Query the KB with Natural Language")
    p_query.add_argument(
        "sentence", nargs="+", help='The English query (e.g., "Is Socrates mortal?")'
    )

    # List command
    subparsers.add_parser("list", help="List all facts and rules in the KB")

    # Clear command
    subparsers.add_parser("clear", help="Clear the Knowledge Base")

    args = parser.parse_args()

    if args.action is None:
        parser.print_help()
        sys.exit(0)

    # Reconstruct sentence from list of words (handles spaces in CLI args)
    if hasattr(args, "sentence"):
        full_sentence = " ".join(args.sentence).strip()

    if args.action == "add":
        cmd_add(full_sentence)
    elif args.action == "query":
        cmd_query(full_sentence)
    elif args.action == "list":
        cmd_list()
    elif args.action == "clear":
        cmd_clear()


if __name__ == "__main__":
    main()
