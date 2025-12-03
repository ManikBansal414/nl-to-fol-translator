# Robust NL-to-FOL Resolution System

This system integrates a Natural Language to First-Order Logic (FOL) translator with a Resolution-based Inference Engine.

## Features
- **NL Translator**: Converts English sentences to FOL formulas using spaCy and Lark.
- **Resolution Engine**: A Python-based FOL resolution prover that supports:
    - CNF Conversion
    - Unification
    - Set of Support Strategy
    - Universal and Existential Quantifiers (via Skolemization)

## Directory Structure
- `main.py`: The entry point for the interactive CLI.
- `translator/`: Contains the NL-to-FOL translation logic.
- `resolution_engine/`: Contains the Resolution Prover (ported to Python 3).
- `benchmarks/`: (Optional) Benchmarking scripts.

## Usage

Run the interactive system:
```bash
python3 main.py
```

### Commands
- `add <sentence>`: Adds a fact to the Knowledge Base.
    - Example: `add All humans are mortal`
    - Example: `add Socrates is a human`
- `query <sentence>`: Checks if a sentence is entailed by the Knowledge Base.
    - Example: `query Is Socrates mortal`
    - Example: `query Some humans are mortal`
- `exit`: Quits the application.

## Examples

**Syllogism:**
```
> add All humans are mortal
> add Socrates is a human
> query Socrates is mortal
Result: TRUE
```

**Chain Reasoning:**
```
> add All dogs are mammals
> add All mammals are animals
> query All dogs are animals
Result: TRUE
```
