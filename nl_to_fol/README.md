# NL → FOL Parser

Lightweight rule-based translator from short English sentences to First-Order Logic (FOL) using spaCy for parsing, a custom matcher, and template-driven rendering.

## Architecture (Concise)
- `parser/nlp.py`: spaCy wrapper (Doc creation).
- `parser/matcher.py`: YAML rule load + placeholder/dependency match.
- `parser/templates.py`: template placeholder → FOL + pretty print.
- `parser/fol_validator.py`: Lark grammar validation.
- `parser/pipeline.py`: sentence → FOL orchestration + IF–THEN parsing.
- `main.py`: CLI front-end.

## How to Run
```bash
python3 -m pip install -r requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
python3 main.py "All humans are mortal"
```

## File Map
- `requirements.txt`: deps.
- `examples/test_sentences.txt`: sample inputs.
- `parser/config.py`: debug flag.
- `parser/data_structures.py`: TokenData, CapturedValue.
- `parser/matcher.py`: rule compile + match engines.
- `parser/templates.py`: render + formatting helpers.
- `parser/pipeline.py`: translate + IF–THEN split.
- `parser/fol_validator.py`: grammar + validate.
- `parser/nlp.py`: spaCy model init.
- `rules/base_rules.yaml`: rule definitions.
- `main.py`: CLI wrapper.

## Segment Notes
- Quantifier rules: map determiners (all/some/no) + copula to forall/exists forms.
- Classification rules: NOUN–NOUN patterns produce subset or intersection predicates.
- Negation: "not" before ADJ/NOUN inserts unary `not`.
- Dependency rules: fall back for verb–subject(+object) when patterns not matched.
- IF–THEN: parsed at pipeline layer; each clause becomes `(A -> B)` joined by `&`.
- Placeholders: `/NOUN`, `/NOUN_2` etc. auto-assigned; aliases allow flexible template references.
- Rendering: predicates capitalized; proper nouns merged; multi-token spans joined with `_`.
- Validation: small Lark grammar enforces operator precedence and quantifier scoping.
