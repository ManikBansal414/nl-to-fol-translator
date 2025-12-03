from latest.translator.nlp import process
from latest.translator.matcher import match_rules, RULE_PATH

print(f"Loading rules from: {RULE_PATH}")

sentences = [
    "All humans are mammals",
    "Alice is a human",
    "Alice is mortal",
    "No cats are dogs"
]

for s in sentences:
    doc = process(s)
    match = match_rules(doc)
    if match:
        rule, slots = match
        print(f"Sentence: '{s}' -> Rule: '{rule.name}'")
    else:
        print(f"Sentence: '{s}' -> No match")
