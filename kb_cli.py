#!/usr/bin/env python
"""Simple CLI to add NL premises to the KB or ask NL queries.

Usage:
  python kb_cli.py add "All humans are mortal"
  python kb_cli.py add "Socrates is human"
  python kb_cli.py query "Is Socrates mortal?"
  python kb_cli.py list
  python kb_cli.py clear
"""
from __future__ import annotations
import argparse
from common.translator import translate_sentence
from common.kb import kb


def cmd_add(sentence: str):
    fol = translate_sentence(sentence)
    if fol.startswith('[ERROR]'):
        print('ERROR translating:', fol)
        return
    ok = kb().add(fol)
    if ok:
        print('Added to KB:', fol)
    else:
        print('Unrecognized formula (not added):', fol)


def cmd_query(sentence: str):
    fol = translate_sentence(sentence)
    if fol.startswith('[ERROR]'):
        print('ERROR translating:', fol)
        return
    entailed, trace = kb().query(fol)
    print('Query FOL:', fol)
    print('Entailed:', entailed)
    print('Trace:')
    for t in trace:
        print(' -', t)


def cmd_list():
    print('Facts:')
    for f in kb().list_facts():
        print(' -', f)
    print('\nRules:')
    for r in kb().list_rules():
        print(' -', f'{r[0]} -> {r[1]}')


def cmd_clear():
    kb().clear()
    print('KB cleared')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['add', 'query', 'list', 'clear'])
    ap.add_argument('sentence', nargs='*')
    args = ap.parse_args()
    sentence = ' '.join(args.sentence).strip()
    if args.action == 'add':
        if not sentence:
            print('Provide a sentence to add.')
            return
        cmd_add(sentence)
    elif args.action == 'query':
        if not sentence:
            print('Provide a sentence to query.')
            return
        cmd_query(sentence)
    elif args.action == 'list':
        cmd_list()
    elif args.action == 'clear':
        cmd_clear()


if __name__ == '__main__':
    main()
