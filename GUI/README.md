# GUI for NL → FOL Translator

A minimal Flask web interface to translate English sentences to FOL using the shared translator and validate with one of three methods (or all): lark, nltk, fomaster.

## Setup

From the project root:

```bash
# Activate your existing venv (recommended)
source .venv/bin/activate

# Install GUI deps (Flask)
pip install -r GUI/requirements.txt

# Ensure spaCy model is available
python -m spacy download en_core_web_sm
```

## Run

```bash
cd GUI
python app.py
# open http://localhost:5000
```

KB actions are available in the same page:

- Translate & Validate (original behavior)
- Add to KB (stores unary facts or universal implication rules)
- Query KB (attempts forward chaining proof for unary fact)
- Clear KB (empties persisted store `kb_store.json`)

Supported KB formula patterns (from NL translator):

- `forall x. (Predicate1(x) -> Predicate2(x))`
- `Predicate(Constant)`

Example usage:

1. Add rule: "All humans are mortal" → `forall x. (Human(x) -> Mortal(x))`
2. Add fact: "Socrates is human" → `Human(Socrate)`
3. Query: "Socrates is mortal" → entailed True with derivation trace.

Alternatively:

```bash
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

## Notes

- This GUI reuses the shared code in `translator/`, `knowledge_base/`, `method_lark/`, `method_nltk/`, and `method_fomaster/` without modifying them.
- Choose a method from the dropdown: `lark`, `nltk`, `fomaster`, or `all`.
- If you see an error about missing spaCy model, run the download command above.
